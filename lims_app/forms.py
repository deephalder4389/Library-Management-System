from datetime import date
from pathlib import Path

from django import forms

from .models import Book


class BookUploadForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = [
            'title', 'author', 'publisher', 'isbn', 'publication_year',
            'cover_image', 'pdf_file',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Book title'}),
            'author': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Author name'}),
            'publisher': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Publisher (optional)'}),
            'isbn': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ISBN (optional)'}),
            'publication_year': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Publication year', 'min': '1450'}),
            'cover_image': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'pdf_file': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.pdf,application/pdf'}),
        }

    def clean_publication_year(self):
        year = self.cleaned_data.get('publication_year')
        if year is not None and not (1450 <= year <= date.today().year + 1):
            raise forms.ValidationError('Enter a valid publication year.')
        return year

    def clean_cover_image(self):
        image = self.cleaned_data.get('cover_image')
        if image and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Cover image must be 5 MB or smaller.')
        return image

    def clean_pdf_file(self):
        pdf = self.cleaned_data.get('pdf_file')
        if not pdf:
            return pdf
        if Path(pdf.name).suffix.lower() != '.pdf':
            raise forms.ValidationError('Please select a PDF file.')
        if pdf.size > 20 * 1024 * 1024:
            raise forms.ValidationError('PDF must be 20 MB or smaller.')
        if pdf.size < 5:
            raise forms.ValidationError('The selected PDF file is invalid.')
        # Extension checks alone are insufficient: also verify the file header.
        header = pdf.read(5)
        pdf.seek(0)
        if header != b'%PDF-':
            raise forms.ValidationError('The uploaded file does not appear to be a PDF.')
        return pdf
