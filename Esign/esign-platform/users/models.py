# users/models.py

import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


class UserManager(BaseUserManager):
    """
    Custom manager because we replaced 'username' with 'email'.
    Django's default manager won't work without this.
    """

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)  # lowercases domain part
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # hashes the password
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.ADMIN)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Our custom User model.
    - Email is the login identifier (not username)
    - Role defines what the user can do in the system
    - UUID primary key for security (doesn't expose row count)
    """

    class Role(models.TextChoices):
        SENDER = 'SENDER', 'Sender'
        ADMIN = 'ADMIN', 'Admin'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.SENDER)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # required for admin panel access

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'       # this field is used for login
    REQUIRED_FIELDS = ['first_name', 'last_name']  # asked when using createsuperuser

    def __str__(self):
        return f"{self.email} ({self.role})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()