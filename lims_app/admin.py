from django.contrib import admin
from .models import reader, Book, BookLoan


@admin.register(reader)
class ReaderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'reader_name', 'reader_contact',
        'reference_id', 'reader_address', 'active',
    )
    list_display_links = ('id', 'reader_name')
    list_filter = ('active',)
    search_fields = ('reader_name', 'reader_contact', 'reference_id')
    list_per_page = 25


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'title', 'author', 'publisher',
        'isbn', 'publication_year', 'uploaded_at',
    )
    list_display_links = ('id', 'title')
    search_fields = ('title', 'author', 'publisher', 'isbn')
    list_filter = ('publication_year', 'uploaded_at')
    readonly_fields = ('uploaded_at',)
    list_per_page = 25


class LoanStatusFilter(admin.SimpleListFilter):
    title = 'loan status'
    parameter_name = 'loan_status'

    def lookups(self, request, model_admin):
        return [('issued', 'Issued'), ('returned', 'Returned')]

    def queryset(self, request, queryset):
        if self.value() == 'issued':
            return queryset.filter(returned_at__isnull=True)
        if self.value() == 'returned':
            return queryset.filter(returned_at__isnull=False)
        return queryset


@admin.register(BookLoan)
class BookLoanAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'reader_id_snapshot', 'reader_name_snapshot',
        'book_title_snapshot', 'checkout_at', 'due_at',
        'returned_at', 'loan_status',
    )
    list_display_links = ('id', 'book_title_snapshot')
    search_fields = (
        'reader_name_snapshot', 'book_title_snapshot',
        '=reader_id_snapshot', '=book_id_snapshot',
    )
    list_filter = (LoanStatusFilter, 'checkout_at', 'due_at')
    readonly_fields = (
        'book', 'reader',
        'book_id_snapshot', 'book_title_snapshot',
        'reader_id_snapshot', 'reader_name_snapshot',
        'checkout_at', 'due_at', 'returned_at',
    )
    list_per_page = 25

    @admin.display(description='Status')
    def loan_status(self, obj):
        return 'Returned' if obj.returned_at is not None else 'Issued'

    def has_add_permission(self, request):
        # Loan records must be created through My Bag checkout.
        return False

    def has_delete_permission(self, request, obj=None):
        # Preserve the checkout/return audit history.
        return False

    def has_change_permission(self, request, obj=None):
        # Manage returns through the Returns page, not Django Admin.
        return False
