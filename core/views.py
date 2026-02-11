from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import Q, Count, Sum, Prefetch
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from .models import User, Society, Flat, Tenant, MaintenanceBill
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

# ============= PUBLIC VIEWS =============

def index(request):
    """Landing page"""
    if request.user.is_authenticated:
        if request.user.role == 'ADMIN':
            return redirect('core:admin_dashboard')
        elif request.user.role == 'OWNER':
            return redirect('core:owner_dashboard')
        elif request.user.role == 'TENANT':
            return redirect('core:tenant_dashboard')
    return render(request, 'index.html')


def user_login(request):
    """Login view for all users"""
    if request.user.is_authenticated:
        return redirect('core:index')
    
    if request.method == 'POST':
        email_or_username = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        
        if not email_or_username or not password:
            messages.error(request, 'Please provide both email/username and password.')
            return render(request, 'login.html')

        user = authenticate(request, username=email_or_username, password=password)
        
        if not user:
            try:
                user_obj = User.objects.get(email=email_or_username)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass
        
        if user:
            if user.is_active:
                login(request, user)
                messages.success(request, f'Welcome back, {user.first_name}!')
                
                if user.role == 'ADMIN':
                    return redirect('core:admin_dashboard')
                elif user.role == 'OWNER':
                    return redirect('core:owner_dashboard')
                elif user.role == 'TENANT':
                    return redirect('core:tenant_dashboard')
            else:
                messages.error(request, 'Your account is currently inactive. Please contact the administrator.')
        else:
            messages.error(request, 'Invalid email/username or password.')
    
    return render(request, 'login.html')


@login_required
def user_logout(request):
    """Logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('core:index')


# ============= DECORATORS =============

def admin_required(view_func):
    """Decorator to check if user is admin"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('core:login')
        if request.user.role != 'ADMIN':
            messages.error(request, 'Access denied. Administrator privileges required.')
            return redirect('core:index')
        return view_func(request, *args, **kwargs)
    return wrapper


def owner_required(view_func):
    """Decorator to check if user is owner"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('core:login')
        if request.user.role != 'OWNER':
            messages.error(request, 'Access denied. Owner privileges required.')
            return redirect('core:index')
        return view_func(request, *args, **kwargs)
    return wrapper


def tenant_required(view_func):
    """Decorator to check if user is tenant"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('core:login')
        if request.user.role != 'TENANT':
            messages.error(request, 'Access denied. Tenant privileges required.')
            return redirect('core:index')
        return view_func(request, *args, **kwargs)
    return wrapper


# ============= ADMIN VIEWS =============

@admin_required
def admin_dashboard(request):
    """Admin dashboard"""
    context = {
        'total_societies': Society.objects.count(),
        'total_flats': Flat.objects.count(),
        'total_owners': User.objects.filter(role='OWNER').count(),
        'total_tenants': Tenant.objects.filter(is_active=True).count(),
        'total_bills': MaintenanceBill.objects.count(),
        'unpaid_bills': MaintenanceBill.objects.filter(status='UNPAID').count(),
        'recent_owners': User.objects.filter(role='OWNER').order_by('-date_joined')[:3],
        'recent_bills': MaintenanceBill.objects.filter(status='UNPAID').order_by('-created_at')[:3],
    }
    return render(request, 'admin/admin_dashboard.html', context)


@admin_required
def owner_list(request):
    """List all owners"""
    owners = User.objects.filter(role='OWNER').order_by('-date_joined')
    context = {'owners': owners}
    return render(request, 'admin/owner_list.html', context)

@admin_required
def create_owner(request):
    """Create owner account with automatic email trigger via Signals"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '').strip()
        
        if not all([email, username, first_name, last_name, password]):
            messages.error(request, 'All fields (Email, Username, Name, Password) are required.')
            return redirect('core:owner_list')

        try:
            with transaction.atomic():
                user = User(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone if phone else None,
                    role='OWNER',
                    is_active=True
                )
                user.set_password(password)
                user.full_clean()
                user._plain_password = password
                user.save()

            messages.success(request, f'Owner account for {user.get_full_name()} created successfully.')
            return redirect('core:owner_list')

        except IntegrityError:
            messages.error(request, 'A user with this email or username already exists.')
        except ValidationError as e:
            messages.error(request, f'Validation error: {", ".join(e.messages)}')
        except Exception as e:
            messages.error(request, 'An unexpected error occurred while creating the owner.')
    
    return redirect('core:owner_list')

@admin_required
def update_owner(request, pk):
    """Update existing owner details"""
    owner = get_object_or_404(User, pk=pk, role='OWNER')
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        username = request.POST.get('username', '').strip()
        new_password = request.POST.get('password', '').strip()

        if not all([first_name, last_name, email, username]):
            messages.error(request, 'Name, Email and Username cannot be empty.')
            return redirect('core:owner_list')

        try:
            with transaction.atomic():
                owner.first_name = first_name
                owner.last_name = last_name
                owner.email = email
                owner.phone = phone if phone else None
                owner.username = username
                
                if new_password:
                    owner.set_password(new_password)
                
                owner.full_clean()
                owner.save()
            messages.success(request, f'Owner details for {owner.get_full_name()} updated successfully.')
            
        except IntegrityError:
            messages.error(request, 'The provided email or username is already in use by another account.')
        except ValidationError as e:
            messages.error(request, f'Validation error: {", ".join(e.messages)}')
        except Exception as e:
            messages.error(request, 'An system error occurred while updating the owner.')
            
    return redirect('core:owner_list')

@admin_required
def delete_owner(request, pk):
    """Delete an owner"""
    owner = get_object_or_404(User, pk=pk, role='OWNER')
    try:
        name = owner.get_full_name()
        owner.delete()
        messages.success(request, f'Owner {name} has been deleted permanently.')
    except IntegrityError:
        messages.error(request, 'Cannot delete this owner because they are assigned to flats or have active records.')
    except Exception as e:
        messages.error(request, 'An unexpected error occurred during deletion.')
        
    return redirect('core:owner_list')

@admin_required
def toggle_owner_status(request, pk):
    """Activate/Deactivate owner"""
    owner = get_object_or_404(User, pk=pk, role='OWNER')
    try:
        owner.is_active = not owner.is_active
        owner.save()
        status = 'activated' if owner.is_active else 'deactivated'
        messages.success(request, f'Owner {owner.get_full_name()} has been {status}.')
    except Exception as e:
        messages.error(request, 'Failed to change owner status.')
        
    return redirect('core:owner_list')


@admin_required
def create_society(request):
    """Create society"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        address = request.POST.get('address', '').strip()
        
        if not name or not address:
            messages.error(request, 'Society Name and Address are required.')
        else:
            try:
                society = Society(name=name, address=address)
                society.full_clean()
                society.save()
                messages.success(request, f'Society "{society.name}" created successfully.')
                return redirect('core:society_list')
            except ValidationError as e:
                messages.error(request, f'Validation error: {", ".join(e.messages)}')
            except Exception as e:
                messages.error(request, 'An unexpected error occurred while creating the society.')
    
    return render(request, 'admin/society_list.html')

@admin_required
def update_society(request, pk):
    """Update existing society"""
    society = get_object_or_404(Society, pk=pk)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        address = request.POST.get('address', '').strip()
        
        if not name or not address:
            messages.error(request, 'Society Name and Address are required.')
        else:
            try:
                society.name = name
                society.address = address
                society.full_clean()
                society.save()
                messages.success(request, f'Society "{society.name}" updated successfully.')
            except ValidationError as e:
                messages.error(request, f'Validation error: {", ".join(e.messages)}')
            except Exception as e:
                messages.error(request, 'An unexpected error occurred while updating the society.')
            
    return redirect('core:society_list')

@admin_required
def delete_society(request, pk):
    """Delete a society"""
    society = get_object_or_404(Society, pk=pk)
    try:
        name = society.name
        society.delete()
        messages.success(request, f'Society "{name}" deleted successfully.')
    except IntegrityError:
        messages.error(request, f'Cannot delete Society "{society.name}" because it contains flats.')
    except Exception as e:
        messages.error(request, 'An unexpected error occurred during deletion.')
        
    return redirect('core:society_list')

@admin_required
def society_list(request):
    """List all societies"""
    societies = Society.objects.all().annotate(flat_count=Count('flats'))
    context = {'societies': societies}
    return render(request, 'admin/society_list.html', context)


@admin_required
def flat_list(request):
    """List all flats"""
    flats = Flat.objects.all().select_related('society', 'owner').order_by('-created_at')
    societies = Society.objects.all()
    owners = User.objects.filter(role='OWNER', is_active=True)
    
    context = {
        'flats': flats,
        'societies': societies, 
        'owners': owners        
    }
    return render(request, 'admin/flat_list.html', context)

@admin_required
def create_flat(request):
    """Create flat"""
    societies = Society.objects.all()
    owners = User.objects.filter(role='OWNER', is_active=True)
    
    if request.method == 'POST':
        society_id = request.POST.get('society')
        flat_number = request.POST.get('flat_number', '').strip()
        owner_id = request.POST.get('owner')
        
        if not society_id or not flat_number:
            messages.error(request, 'Society and Flat Number are required.')
            return redirect('core:flat_list')

        if not society_id.isdigit():
            messages.error(request, 'Invalid Society ID.')
            return redirect('core:flat_list')
            
        try:
            society = Society.objects.get(id=int(society_id))
            
            owner = None
            if owner_id and owner_id.strip():
                if not owner_id.isdigit():
                     messages.error(request, 'Invalid Owner ID.')
                     return redirect('core:flat_list')
                try:
                    owner = User.objects.get(id=int(owner_id), role='OWNER')
                except User.DoesNotExist:
                    messages.error(request, 'The selected owner does not exist.')
                    return redirect('core:flat_list')

            flat = Flat(
                society=society,
                flat_number=flat_number,
                owner=owner
            )
            flat.full_clean()
            flat.save()
            messages.success(request, f'Flat {flat.flat_number} created successfully in {society.name}.')
            return redirect('core:flat_list')
            
        except ObjectDoesNotExist:
            messages.error(request, 'Invalid Society selected.')
        except IntegrityError:
            messages.error(request, f'Flat {flat_number} already exists in this society.')
        except ValidationError as e:
            messages.error(request, f'Validation error: {", ".join(e.messages)}')
        except Exception as e:
            messages.error(request, 'An unexpected error occurred while creating the flat.')
            return redirect('core:flat_list')
    
    context = {'societies': societies, 'owners': owners}
    return render(request, 'admin/flat_list.html', context)

@admin_required
def update_flat(request, pk):
    """Update existing flat"""
    flat = get_object_or_404(Flat, pk=pk)
    
    if request.method == 'POST':
        society_id = request.POST.get('society')
        flat_number = request.POST.get('flat_number', '').strip()
        owner_id = request.POST.get('owner')

        if not society_id or not flat_number:
            messages.error(request, 'Society and Flat Number are required.')
            return redirect('core:flat_list')

        if not society_id.isdigit():
            messages.error(request, 'Invalid Society ID.')
            return redirect('core:flat_list')

        try:
            flat.society = get_object_or_404(Society, pk=int(society_id))
            flat.flat_number = flat_number
            
            if owner_id and owner_id.strip():
                if not owner_id.isdigit():
                     messages.error(request, 'Invalid Owner ID.')
                     return redirect('core:flat_list')
                flat.owner = get_object_or_404(User, pk=int(owner_id), role='OWNER')
            else:
                flat.owner = None
            
            flat.full_clean()
            flat.save()
            messages.success(request, f'Flat {flat.flat_number} updated successfully.')
            
        except IntegrityError:
            messages.error(request, 'A flat with this number already exists in the selected society.')
        except ValidationError as e:
            messages.error(request, f'Validation error: {", ".join(e.messages)}')
        except Exception as e:
            messages.error(request, 'An unexpected error occurred while updating the flat.')
            
    return redirect('core:flat_list')

@admin_required
def delete_flat(request, pk):
    """Delete a flat"""
    flat = get_object_or_404(Flat, pk=pk)
    try:
        number = flat.flat_number
        flat.delete()
        messages.success(request, f'Flat {number} deleted successfully.')
    except IntegrityError:
        messages.error(request, 'Cannot delete this flat because it has associated bills or tenants.')
    except Exception as e:
        messages.error(request, 'An unexpected error occurred during deletion.')
        
    return redirect('core:flat_list')

@admin_required
def bill_list(request):
    """List all bills with Context for Create Modal"""
    bills = MaintenanceBill.objects.all().select_related('flat', 'flat__owner', 'flat__society').order_by('-year', '-created_at')
    flats = Flat.objects.filter(owner__isnull=False).select_related('owner', 'society')
    months = MaintenanceBill.MONTH_CHOICES
    
    current_year = datetime.now().year
    current_month = datetime.now().month

    context = {
        'bills': bills,
        'flats': flats,
        'months': months,
        'current_year': current_year,
        'current_month': current_month
    }
    return render(request, 'admin/bill_list.html', context)


@admin_required
def create_bill(request):
    """Create maintenance bill (Handles POST from Page AND Modal)"""
    flats = Flat.objects.filter(owner__isnull=False).select_related('owner', 'society')
    months = MaintenanceBill.MONTH_CHOICES
    current_year = datetime.now().year

    if request.method == 'POST':
        flat_id = request.POST.get('flat')
        month = request.POST.get('month')
        year = request.POST.get('year')
        amount = request.POST.get('amount')
        status = request.POST.get('status', 'UNPAID')
        
        if not all([flat_id, month, year, amount]):
             messages.error(request, 'All fields (Flat, Month, Year, Amount) are required.')
             return redirect('core:bill_list')

        if not flat_id.isdigit():
             messages.error(request, 'Invalid Flat ID.')
             return redirect('core:bill_list')

        try:
            try:
                year_val = int(year)
                amount_val = Decimal(amount)
            except (ValueError, InvalidOperation):
                messages.error(request, 'Invalid format for Year or Amount.')
                return redirect('core:bill_list')

            flat = get_object_or_404(Flat, id=int(flat_id))
            
            bill = MaintenanceBill(
                flat=flat,
                month=month,
                year=year_val,
                amount=amount_val,
                status=status
            )
            bill.full_clean()
            bill.save()
            messages.success(request, f'Bill generated for {flat.flat_number} ({month} {year}) successfully.')
            return redirect('core:bill_list')
            
        except IntegrityError:
            messages.error(request, 'A bill for this flat, month, and year already exists.')
        except ValidationError as e:
            messages.error(request, f'Validation error: {", ".join(e.messages)}')
        except Exception as e:
            messages.error(request, 'An unexpected error occurred while generating the bill.')
    
    context = {
        'flats': flats,
        'months': months,
        'current_year': current_year
    }
    return render(request, 'admin/bill_list.html', context)


@admin_required
def toggle_bill_status(request, pk):
    """Toggle bill payment status"""
    bill = get_object_or_404(MaintenanceBill, pk=pk)
    
    try:
        bill.status = 'PAID' if bill.status == 'UNPAID' else 'UNPAID'
        bill.save()
        action = "marked as PAID" if bill.status == 'PAID' else "marked as UNPAID"
        messages.success(request, f'Bill for Flat {bill.flat.flat_number} {action}.')
    except Exception as e:
        messages.error(request, 'Failed to update bill status.')
    
    return redirect('core:bill_list')

@admin_required
def update_bill(request, pk):
    """Update existing bill"""
    bill = get_object_or_404(MaintenanceBill, pk=pk)
    
    if request.method == 'POST':
        flat_id = request.POST.get('flat')
        month = request.POST.get('month')
        year = request.POST.get('year')
        amount = request.POST.get('amount')
        status = request.POST.get('status')

        if not all([flat_id, month, year, amount, status]):
             messages.error(request, 'All fields are required.')
             return redirect('core:bill_list')

        if not flat_id.isdigit():
             messages.error(request, 'Invalid Flat ID.')
             return redirect('core:bill_list')

        try:
            try:
                year_val = int(year)
                amount_val = Decimal(amount)
            except (ValueError, InvalidOperation):
                messages.error(request, 'Invalid format for Year or Amount.')
                return redirect('core:bill_list')

            bill.flat = get_object_or_404(Flat, pk=int(flat_id))
            bill.month = month
            bill.year = year_val
            bill.amount = amount_val
            bill.status = status
            
            bill.full_clean()
            bill.save()
            messages.success(request, 'Bill updated successfully.')
            
        except IntegrityError:
            messages.error(request, 'A bill with these details already exists.')
        except ValidationError as e:
            messages.error(request, f'Validation error: {", ".join(e.messages)}')
        except Exception as e:
            messages.error(request, 'An unexpected error occurred while updating the bill.')
            
    return redirect('core:bill_list')

@admin_required
def delete_bill(request, pk):
    """Delete a bill"""
    bill = get_object_or_404(MaintenanceBill, pk=pk)
    try:
        bill.delete()
        messages.success(request, 'Bill deleted successfully.')
    except Exception as e:
        messages.error(request, 'An unexpected error occurred while deleting the bill.')
        
    return redirect('core:bill_list')


# ============= OWNER VIEWS =============

@owner_required
def owner_dashboard(request):
    """Owner dashboard"""
    my_flats = Flat.objects.filter(owner=request.user)
    my_tenants = Tenant.objects.filter(flat__owner=request.user, is_active=True)
    my_bills = MaintenanceBill.objects.filter(flat__owner=request.user).order_by('-year', '-created_at')[:3]
    
    total_bills = MaintenanceBill.objects.filter(flat__owner=request.user)
    unpaid_bills = total_bills.filter(status='UNPAID')
    
    context = {
        'my_flats': my_flats,
        'total_flats': my_flats.count(),
        'total_tenants': my_tenants.count(),
        'total_bills': total_bills.count(),
        'unpaid_bills': unpaid_bills.count(),
        'recent_bills': my_bills,
    }
    return render(request, 'owner/owner_dashboard.html', context)


@owner_required
def owner_flats(request):
    """Owner's flats with Active Tenant Prefetch"""
    flats = Flat.objects.filter(owner=request.user).select_related('society').prefetch_related(
        Prefetch('tenants', queryset=Tenant.objects.filter(is_active=True).select_related('user'), to_attr='active_tenant_list')
    )
    
    context = {'flats': flats}
    return render(request, 'owner/owner_flats.html', context)


@owner_required
def owner_bills(request):
    """Owner's maintenance bills"""
    bills = MaintenanceBill.objects.filter(flat__owner=request.user).select_related('flat').order_by('-year', '-created_at')
    
    status_filter = request.GET.get('status')
    if status_filter:
        bills = bills.filter(status=status_filter)
    
    context = {'bills': bills, 'status_filter': status_filter}
    return render(request, 'owner/owner_bills.html', context)


@owner_required
def create_tenant(request):
    """Owner creates tenant with automatic email trigger"""
    my_flats = Flat.objects.filter(owner=request.user)
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '').strip()
        
        flat_id = request.POST.get('flat')
        rent_amount = request.POST.get('rent_amount')
        start_date = request.POST.get('start_date')
        
        if not all([email, username, first_name, last_name, password, flat_id, rent_amount, start_date]):
             messages.error(request, 'All fields are required.')
             return redirect('core:tenant_list')

        if not flat_id.isdigit():
             messages.error(request, 'Invalid Flat ID.')
             return redirect('core:tenant_list')

        try:
            try:
                rent_val = Decimal(rent_amount)
                # Ensure date format is correct if needed, mostly handled by date input but good to verify
                datetime.strptime(start_date, '%Y-%m-%d')
            except (ValueError, InvalidOperation):
                messages.error(request, 'Invalid format for Rent or Date.')
                return redirect('core:tenant_list')

            with transaction.atomic():
                flat = get_object_or_404(Flat, id=int(flat_id), owner=request.user)
                
                user = User(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone if phone else None,
                    role='TENANT',
                    is_active=True
                )
                user.set_password(password)
                user.full_clean()
                user._plain_password = password
                user.save()
                
                tenant = Tenant(
                    user=user,
                    flat=flat,
                    rent_amount=rent_val,
                    start_date=start_date,
                    is_active=True
                )
                tenant.full_clean()
                tenant.save()
            
            messages.success(request, f'Tenant {user.get_full_name()} created successfully.')
            return redirect('core:tenant_list')
            
        except IntegrityError:
            messages.error(request, 'A user with this email or username already exists, or the flat already has an active tenant.')
        except ValidationError as e:
            messages.error(request, f'Validation error: {", ".join(e.messages)}')
        except ObjectDoesNotExist:
            messages.error(request, 'Invalid Flat selected.')
        except Exception as e:
            messages.error(request, 'An system error occurred while creating the tenant.')
    
    context = {'my_flats': my_flats}
    return render(request, 'owner/tenant_list.html', context)

@owner_required
def tenant_list(request):
    """Owner's tenants"""
    tenants = Tenant.objects.filter(flat__owner=request.user).select_related('user', 'flat')
    my_flats = Flat.objects.filter(owner=request.user)
    context = {'tenants': tenants,'my_flats': my_flats}
    return render(request, 'owner/tenant_list.html', context)


@owner_required
def toggle_tenant_status(request, pk):
    """Activate/Deactivate tenant"""
    tenant = get_object_or_404(Tenant, pk=pk, flat__owner=request.user)
    try:
        tenant.is_active = not tenant.is_active
        tenant.save()
        status = 'activated' if tenant.is_active else 'deactivated'
        messages.success(request, f'Tenant {tenant.user.get_full_name()} {status}.')
    except Exception as e:
        messages.error(request, 'Failed to update tenant status.')
        
    return redirect('core:tenant_list')

@owner_required
def update_tenant(request, pk):
    """Updates tenant details from the modal"""
    tenant = get_object_or_404(Tenant, pk=pk, flat__owner=request.user)
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        username = request.POST.get('username', '').strip()
        phone = request.POST.get('phone', '').strip()
        
        flat_id = request.POST.get('flat')
        rent_amount = request.POST.get('rent_amount')
        start_date = request.POST.get('start_date')

        if not all([first_name, last_name, email, username, flat_id, rent_amount, start_date]):
             messages.error(request, 'All fields are required.')
             return redirect('core:tenant_list')

        if not flat_id.isdigit():
             messages.error(request, 'Invalid Flat ID.')
             return redirect('core:tenant_list')

        try:
            try:
                rent_val = Decimal(rent_amount)
                datetime.strptime(start_date, '%Y-%m-%d')
            except (ValueError, InvalidOperation):
                messages.error(request, 'Invalid format for Rent or Date.')
                return redirect('core:tenant_list')

            with transaction.atomic():
                user = tenant.user
                user.first_name = first_name
                user.last_name = last_name
                user.email = email
                user.username = username
                user.phone = phone if phone else None
                user.full_clean()
                user.save()

                tenant.flat = get_object_or_404(Flat, id=int(flat_id), owner=request.user)
                tenant.rent_amount = rent_val
                tenant.start_date = start_date
                tenant.full_clean()
                tenant.save()

            messages.success(request, f'Tenant {user.get_full_name()} updated successfully.')
        except IntegrityError:
            messages.error(request, 'Email or Username already in use.')
        except ValidationError as e:
            messages.error(request, f'Validation error: {", ".join(e.messages)}')
        except Exception as e:
            messages.error(request, 'An unexpected error occurred while updating the tenant.')
            
    return redirect('core:tenant_list')

@owner_required
def delete_tenant(request, pk):
    """Deletes a tenant"""
    if request.method == 'POST':
        tenant = get_object_or_404(Tenant, pk=pk, flat__owner=request.user)
        user = tenant.user
        try:
            with transaction.atomic():
                tenant.delete()
                user.delete() 
            messages.success(request, 'Tenant account deleted successfully.')
        except Exception as e:
            messages.error(request, 'An unexpected error occurred during deletion.')
            
    return redirect('core:tenant_list')


# ============= TENANT VIEWS =============

@tenant_required
def tenant_dashboard(request):
    """Tenant dashboard"""
    try:
        tenant = Tenant.objects.get(user=request.user)
        context = {
            'tenant': tenant,
            'flat': tenant.flat,
            'society': tenant.flat.society,
        }
    except Tenant.DoesNotExist:
        context = {'tenant': None}
    
    return render(request, 'tenant/tenant_dashboard.html', context)


@tenant_required
def tenant_flat(request):
    """Tenant's flat details"""
    try:
        tenant = Tenant.objects.get(user=request.user)
        context = {
            'tenant': tenant,
            'flat': tenant.flat,
            'society': tenant.flat.society,
            'owner': tenant.flat.owner,
        }
    except Tenant.DoesNotExist:
        context = {'tenant': None}
    
    return render(request, 'tenant/tenant_flat.html', context)