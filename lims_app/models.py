from django.db import models

# Create your models here.
class reader(models.Model):
    def __str__(self):
        return self.reader_name
    reference_id=models.CharField(max_length=200)
    reader_name=models.CharField(max_length=200)
    reader_contact=models.CharField(max_length=200)
    reader_address=models.TextField()
    active=models.BooleanField(default=True)


class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=200)
    publisher = models.CharField(max_length=200, blank=True)
    isbn = models.CharField(max_length=20, blank=True)
    publication_year = models.PositiveIntegerField(null=True, blank=True)
    cover_image = models.ImageField(upload_to='book_covers/', blank=True)
    pdf_file = models.FileField(upload_to='book_pdfs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class BookLoan(models.Model):
    """A persisted checkout. Snapshots retain history if a book/reader is later deleted."""
    book = models.ForeignKey(Book, null=True, blank=True, on_delete=models.SET_NULL, related_name='loans')
    reader = models.ForeignKey(reader, null=True, blank=True, on_delete=models.SET_NULL, related_name='book_loans')
    book_id_snapshot = models.PositiveIntegerField()
    book_title_snapshot = models.CharField(max_length=255)
    reader_id_snapshot = models.PositiveIntegerField()
    reader_name_snapshot = models.CharField(max_length=200)
    checkout_at = models.DateTimeField()
    due_at = models.DateTimeField()
    returned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-checkout_at', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['book'],
                condition=models.Q(returned_at__isnull=True),
                name='one_active_loan_per_book',
            ),
        ]

    def __str__(self):
        return f'{self.book_title_snapshot} issued to {self.reader_name_snapshot}'
