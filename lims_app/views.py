from django.shortcuts import render
from django.contrib import admin
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import HttpResponseBadRequest
from django.db import transaction
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import IntegrityError
from django.core.paginator import Paginator
from .models import BookLoan

logger = logging.getLogger(__name__)
from .models import *
# Create your views here.

def home(request):
    return render(request,"home.html",context={"current_tab": "home"})

# def readers(request):
#     return render(request,"readers.html",context={"current_tab": "readers"})

def readers(request):
    if request.method=='GET':
        readers = reader.objects.all()   # ADDED

        return render(
            request,
            "readers.html",
            context={
                "current_tab": "readers",
                "readers": readers        # ADDED
            }
        )
    else:
        query = request.POST['query']
        readers = reader.objects.filter(reader_name__icontains=query)
        return render(
                    request,
                    "readers.html",
                    context={
                        "current_tab": "readers",
                        "readers": readers,
                        "query": query               # ADDED
                    }
                )

def shop(request):
    return HttpResponse("welcome to Shopping")

def save_student(request):
    student_name = request.POST['student_name']
    return HttpResponse("Welcome to library - "+student_name)

# def readers_tab(request):
#     readers = reader.objects.all()
#     return render(request,"readers.html",context={"current_tab": "readers", "readers":readers})

def save_reader(request):
    reader_item = reader(reference_id=request.POST['reader_ref_id'],
                        reader_name=request.POST['reader_name' ],
                        reader_contact=request.POST['reader_contact'],
                        reader_address=request.POST[ 'reader_address' ],
                        active=True
                        )
    reader_item.save()
    return redirect('/readers')


@require_POST
def update_reader(request, reader_id):
    reader_item = get_object_or_404(reader, pk=reader_id)
    name = request.POST.get('reader_name', '').strip()
    contact = request.POST.get('reader_contact', '').strip()
    ref_id = request.POST.get('reader_ref_id', '').strip()
    address = request.POST.get('reader_address', '').strip()

    if not name or not contact or not ref_id:
        return HttpResponseBadRequest('Name, contact and reference ID are required.')

    reader_item.reader_name = name
    reader_item.reader_contact = contact
    reader_item.reference_id = ref_id
    reader_item.reader_address = address
    reader_item.save()
    return redirect('/readers')


@require_POST
def deactivate_reader(request, reader_id):
    reader_item = get_object_or_404(reader, pk=reader_id, active=True)
    reader_item.active = False
    reader_item.save(update_fields=['active'])
    return redirect('/readers')


@require_POST
def activate_reader(request, reader_id):
    reader_item = get_object_or_404(reader, pk=reader_id, active=False)
    reader_item.active = True
    reader_item.save(update_fields=['active'])
    return redirect('/readers')


@require_POST
def delete_reader(request, reader_id):
    """Permanently remove a reader after a confirmed POST request."""
    reader_item = get_object_or_404(reader, pk=reader_id)
    if BookLoan.objects.filter(reader=reader_item, returned_at__isnull=True).exists():
        return HttpResponseBadRequest("This reader has unreturned books. Return them before deleting the reader.")
    reader_item.delete()
    return redirect('/readers')


# Book catalogue and single-book upload
from django.contrib import messages
from django.db.models import Q
from .forms import BookUploadForm
from .models import Book


def books(request):
    query = request.GET.get('q', '').strip()
    uploaded_books = Book.objects.all().order_by('-uploaded_at', '-id')
    if query:
        uploaded_books = uploaded_books.filter(
            Q(title__icontains=query) |
            Q(author__icontains=query) |
            Q(publisher__icontains=query) |
            Q(isbn__icontains=query)
        )

    return render(request, 'books.html', {
        'current_tab': 'books',
        'books': uploaded_books,
        'query': query,
        'total_books': Book.objects.count(),
        'form': BookUploadForm(),
        'open_upload_modal': False,
        'bag_ids': _bag_ids(request),
        'issued_book_ids': list(BookLoan.objects.filter(returned_at__isnull=True, book__isnull=False).values_list('book_id', flat=True)),
    })


@require_POST
def upload_book(request):
    form = BookUploadForm(request.POST, request.FILES)
    if form.is_valid():
        new_book = form.save()
        messages.success(request, f'"{new_book.title}" uploaded successfully.')
        return redirect('books')

    # Keep validation messages in the upload dialog instead of losing them.
    return render(request, 'books.html', {
        'current_tab': 'books',
        'books': Book.objects.all().order_by('-uploaded_at', '-id'),
        'query': '',
        'total_books': Book.objects.count(),
        'form': form,
        'open_upload_modal': True,
        'bag_ids': _bag_ids(request),
        'issued_book_ids': list(BookLoan.objects.filter(returned_at__isnull=True, book__isnull=False).values_list('book_id', flat=True)),
    }, status=400)


@require_POST
@transaction.atomic
def delete_book(request, book_id):
    """Delete a book and clean up its uploads after the DB transaction commits."""
    book_item = get_object_or_404(Book, pk=book_id)
    if BookLoan.objects.filter(book=book_item, returned_at__isnull=True).exists():
        messages.error(request, 'This book is currently issued. It must be returned before deletion.')
        return redirect('books')
    title = book_item.title
    files_to_remove = [
        (field.storage, field.name)
        for field in (book_item.pdf_file, book_item.cover_image)
        if field.name
    ]

    book_item.delete()

    def remove_uploaded_files():
        for storage, filename in files_to_remove:
            try:
                storage.delete(filename)
            except Exception:
                logger.exception('Could not remove deleted book file: %s', filename)

    transaction.on_commit(remove_uploaded_files)
    messages.success(request, f'"{title}" deleted successfully.')
    return redirect('books')


# ------------------------- MY BAG / CHECKOUT -------------------------
BAG_SESSION_KEY = 'library_book_bag'
MAX_BOOKS_PER_READER = 4
MAX_LOAN_DAYS = 14


def _bag_ids(request):
    """Maintain an ordered, unique session bag and remove deleted book IDs."""
    raw = request.session.get(BAG_SESSION_KEY, [])
    if not isinstance(raw, list):
        raw = []
    ids = []
    for value in raw:
        if type(value) is int and value > 0 and value not in ids:
            ids.append(value)
    existing = set(Book.objects.filter(id__in=ids).values_list('id', flat=True))
    clean = [pk for pk in ids if pk in existing]
    if request.session.get(BAG_SESSION_KEY) != clean:
        request.session[BAG_SESSION_KEY] = clean
    return clean


@require_POST
def add_to_bag(request, book_id):
    book_item = get_object_or_404(Book, pk=book_id)
    bag_ids = _bag_ids(request)
    if BookLoan.objects.filter(book=book_item, returned_at__isnull=True).exists():
        messages.error(request, 'This book is already issued and cannot be added to the bag.')
    elif book_id in bag_ids:
        messages.info(request, 'This book is already in your bag.')
    elif len(bag_ids) >= MAX_BOOKS_PER_READER:
        messages.error(request, 'Only four books can be placed in the bag at once.')
    else:
        request.session[BAG_SESSION_KEY] = bag_ids + [book_id]
        messages.success(request, f'Added "{book_item.title}" to your bag.')
    return redirect('books')


@require_POST
def remove_from_bag(request, book_id):
    bag_ids = _bag_ids(request)
    if book_id in bag_ids:
        request.session[BAG_SESSION_KEY] = [pk for pk in bag_ids if pk != book_id]
        messages.info(request, 'Book removed from your bag.')
    return redirect('my_bag')


def my_bag(request):
    bag_ids = _bag_ids(request)
    books_by_id = Book.objects.in_bulk(bag_ids)
    selected_books = [books_by_id[pk] for pk in bag_ids]
    lookup_id = request.GET.get('reader_id', '').strip()
    chosen_reader = None
    lookup_error = ''
    if lookup_id:
        if not lookup_id.isdecimal():
            lookup_error = 'Enter a valid numeric Reader ID.'
        else:
            chosen_reader = reader.objects.filter(pk=int(lookup_id)).first()
            if chosen_reader is None:
                lookup_error = 'No reader found with this ID.'
            elif not chosen_reader.active:
                lookup_error = 'This reader is deactivated. Activate the reader before checkout.'

    now = timezone.now()
    local_now = timezone.localtime(now) if timezone.is_aware(now) else now
    max_due = now + timedelta(days=MAX_LOAN_DAYS)
    local_max_due = timezone.localtime(max_due) if timezone.is_aware(max_due) else max_due
    issued = set(BookLoan.objects.filter(book_id__in=bag_ids, returned_at__isnull=True)
                 .values_list('book_id', flat=True))
    return render(request, 'bag.html', {
        'current_tab': 'mybag',
        'bag_books': selected_books,
        'bag_count': len(selected_books),
        'lookup_id': lookup_id,
        'chosen_reader': chosen_reader,
        'lookup_error': lookup_error,
        'checkout_start': local_now,
        'min_due': local_now.strftime('%Y-%m-%dT%H:%M'),
        'max_due': local_max_due.strftime('%Y-%m-%dT%H:%M'),
        'issued_book_ids': issued,
        'max_books': MAX_BOOKS_PER_READER,
    })


@require_POST
def checkout_bag(request):
    bag_ids = _bag_ids(request)
    if not bag_ids:
        messages.error(request, 'Your bag is empty. Add a book before checkout.')
        return redirect('my_bag')
    if len(bag_ids) > MAX_BOOKS_PER_READER:
        messages.error(request, 'You cannot checkout more than four books at once.')
        return redirect('my_bag')

    reader_id = request.POST.get('reader_id', '').strip()
    if not reader_id.isdecimal():
        messages.error(request, 'Look up and select a valid Reader ID.')
        return redirect('my_bag')
    chosen_reader = reader.objects.filter(pk=int(reader_id), active=True).first()
    if chosen_reader is None:
        messages.error(request, 'Reader not found or deactivated.')
        return redirect('my_bag')

    due_text = request.POST.get('due_at', '').strip()
    try:
        due_local = datetime.strptime(due_text, '%Y-%m-%dT%H:%M')
        due_at = timezone.make_aware(due_local, timezone.get_current_timezone()) if timezone.is_aware(timezone.now()) else due_local
    except (ValueError, OverflowError):
        messages.error(request, 'Choose a valid return due date and time.')
        return redirect('my_bag')
    now = timezone.now()
    if due_at <= now or due_at > now + timedelta(days=MAX_LOAN_DAYS):
        messages.error(request, 'Return due date must be in the future and within 14 days.')
        return redirect('my_bag')

    try:
        with transaction.atomic():
            current_reader_loans = BookLoan.objects.filter(reader=chosen_reader, returned_at__isnull=True).count()
            if current_reader_loans + len(bag_ids) > MAX_BOOKS_PER_READER:
                messages.error(request, 'This reader would exceed the four-book borrowing limit.')
                return redirect('my_bag')
            selected = Book.objects.in_bulk(bag_ids)
            if len(selected) != len(bag_ids):
                messages.error(request, 'A selected book was removed. Please check your bag.')
                return redirect('my_bag')
            if BookLoan.objects.filter(book_id__in=bag_ids, returned_at__isnull=True).exists():
                messages.error(request, 'A selected book is already issued. Remove it before checkout.')
                return redirect('my_bag')
            BookLoan.objects.bulk_create([
                BookLoan(
                    book=selected[pk], reader=chosen_reader,
                    book_id_snapshot=pk, book_title_snapshot=selected[pk].title,
                    reader_id_snapshot=chosen_reader.pk, reader_name_snapshot=chosen_reader.reader_name,
                    checkout_at=now, due_at=due_at,
                ) for pk in bag_ids
            ])
    except IntegrityError:
        messages.error(request, 'A selected book became unavailable. Please review your bag.')
        return redirect('my_bag')

    request.session[BAG_SESSION_KEY] = []
    messages.success(request, f'{len(bag_ids)} book(s) checked out to {chosen_reader.reader_name}. Due on {due_at:%d %b %Y, %I:%M %p}.')
    return redirect('my_bag')


# ------------------------- RETURNS / RENTAL TRACKING -------------------------
def returns_page(request):
    """Show outstanding checkouts or completed returns; searchable by reader/book."""
    query = request.GET.get('q', '').strip()[:150]
    status = request.GET.get('status', 'pending')
    if status not in ('pending', 'returned'):
        status = 'pending'

    rentals = BookLoan.objects.select_related('reader', 'book')
    if status == 'returned':
        rentals = rentals.filter(returned_at__isnull=False).order_by('-returned_at', '-pk')
    else:
        rentals = rentals.filter(returned_at__isnull=True).order_by('due_at', 'pk')

    if query:
        match = (Q(reader_name_snapshot__icontains=query) |
                 Q(book_title_snapshot__icontains=query) |
                 Q(reader__reader_contact__icontains=query))
        if query.isdecimal():
            match |= Q(reader_id_snapshot=int(query))
        rentals = rentals.filter(match)

    page_obj = Paginator(rentals, 8).get_page(request.GET.get('page'))
    return render(request, 'returns.html', {
        'current_tab': 'returns',
        'loans': page_obj,
        'rental_count': rentals.count(),
        'query': query,
        'status': status,
        'now': timezone.now(),
    })


@require_POST
def return_loan(request, loan_id):
    """Mark one active loan as returned; do not delete its history or the book."""
    now = timezone.now()
    # Conditional update also prevents two simultaneous submissions from
    # overwriting the original returned_at time.
    changed = BookLoan.objects.filter(
        pk=loan_id, returned_at__isnull=True
    ).update(returned_at=now)
    if changed:
        messages.success(request, 'Book marked as returned. It is now available in the catalogue.')
    elif BookLoan.objects.filter(pk=loan_id).exists():
        messages.info(request, 'This loan was already marked as returned.')
    else:
        get_object_or_404(BookLoan, pk=loan_id)
    return redirect('returns')
