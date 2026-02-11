from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from datetime import date

class User(AbstractUser):
    ADMIN = 'ADMIN'
    OWNER = 'OWNER'
    TENANT = 'TENANT'
    
    ROLE_CHOICES = [
        (ADMIN, 'Admin'),
        (OWNER, 'Owner'),
        (TENANT, 'Tenant'),
    ]
    
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=TENANT)
    phone = models.CharField(max_length=15,blank=True, null=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message='Enter a valid phone number (9-15 digits)'
            )
        ]
    )
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.email
    
    def clean(self):
        super().clean()
        if self.email:
            self.email = self.email.lower().strip()
        
        # Validate first and last name for owners
        if self.role in [self.OWNER, self.TENANT]:
            if not self.first_name or not self.last_name:
                raise ValidationError('First name and last name are required for Owners and Tenants')
    def save(self, *args, **kwargs):
    # ensure any superuser always has ADMIN role
        if self.is_superuser:
            self.role = self.ADMIN
        super().save(*args, **kwargs)

class Society(models.Model):
    name = models.CharField(max_length=200,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9\s\-,.]+$',
                message='Society name can only contain letters, numbers, spaces, hyphens, commas and dots'
            )
        ]
    )
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    def clean(self):
        super().clean()
        if self.name:
            self.name = self.name.strip()
            if len(self.name) < 3:
                raise ValidationError({'name': 'Society name must be at least 3 characters long'})
        
        if self.address:
            self.address = self.address.strip()
            if len(self.address) < 10:
                raise ValidationError({'address': 'Please provide a complete address (minimum 10 characters)'})
    
    class Meta:
        verbose_name_plural = 'Societies'


class Flat(models.Model):
    society = models.ForeignKey(Society, on_delete=models.CASCADE, related_name='flats')
    flat_number = models.CharField(max_length=50,
        validators=[
            RegexValidator(
                regex=r'^[A-Za-z0-9\-/]+$',
                message='Flat number can only contain letters, numbers, hyphens and slashes (e.g., A-101, B/205)'
            )
        ]
    )
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                             related_name='owned_flats', limit_choices_to={'role': 'OWNER'})
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.society.name} - {self.flat_number}"
    
    def clean(self):
        super().clean()
        if self.flat_number:
            self.flat_number = self.flat_number.upper().strip()
        
        # Validate owner role
        if self.owner and self.owner.role != 'OWNER':
            raise ValidationError({'owner': 'Selected user must have OWNER role'})
    
    class Meta:
        unique_together = ['society', 'flat_number']


class Tenant(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, limit_choices_to={'role': 'TENANT'})
    flat = models.ForeignKey(Flat, on_delete=models.CASCADE, related_name='tenants')
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0.01, message='Rent amount must be greater than 0')]
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.flat}"
    
    def clean(self):
        super().clean()
        
        # Validate user role
        if self.user and self.user.role != 'TENANT':
            raise ValidationError({'user': 'Selected user must have TENANT role'})
        
        # Validate dates
        if self.start_date and self.start_date < date(2000, 1, 1):
            raise ValidationError({'start_date': 'Start date cannot be before year 2000'})
        
        if self.end_date:
            if self.end_date <= self.start_date:
                raise ValidationError({'end_date': 'End date must be after start date'})
        
        # Check if tenant already exists for this user
        if self.pk is None:  # Only for new records
            existing = Tenant.objects.filter(user=self.user, is_active=True).exists()
            if existing:
                raise ValidationError({'user': 'This user is already an active tenant'})


class MaintenanceBill(models.Model):
    PAID = 'PAID'
    UNPAID = 'UNPAID'
    
    STATUS_CHOICES = [
        (PAID, 'Paid'),
        (UNPAID, 'Unpaid'),
    ]
    
    MONTH_CHOICES = [
        ('JANUARY', 'January'),
        ('FEBRUARY', 'February'),
        ('MARCH', 'March'),
        ('APRIL', 'April'),
        ('MAY', 'May'),
        ('JUNE', 'June'),
        ('JULY', 'July'),
        ('AUGUST', 'August'),
        ('SEPTEMBER', 'September'),
        ('OCTOBER', 'October'),
        ('NOVEMBER', 'November'),
        ('DECEMBER', 'December'),
    ]
    
    flat = models.ForeignKey(Flat, on_delete=models.CASCADE, related_name='bills')
    month = models.CharField(max_length=20, choices=MONTH_CHOICES)
    year = models.IntegerField(
        validators=[
            MinValueValidator(2000, message='Year must be 2000 or later'),
            MinValueValidator(1900)
        ]
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2,
        validators=[MinValueValidator(1.00, message='Bill amount must be at least ₹1')]
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=UNPAID)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.flat} - {self.month} {self.year}"
    
    def clean(self):
        super().clean()
        
        # Validate year is not in future
        current_year = date.today().year
        if self.year and self.year > current_year + 1:
            raise ValidationError({'year': f'Year cannot be more than {current_year + 1}'})
        
        # Validate flat has owner
        if self.flat and not self.flat.owner:
            raise ValidationError({'flat': 'Cannot create bill for flat without an owner'})
        
        # Check duplicate bill for same flat, month, year
        if self.pk is None:
            existing = MaintenanceBill.objects.filter(
                flat=self.flat,
                month=self.month,
                year=self.year
            ).exists()
            if existing:
                raise ValidationError('A bill for this flat, month and year already exists')
    
    class Meta:
        unique_together = ['flat', 'month', 'year']