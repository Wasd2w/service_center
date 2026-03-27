from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth, TruncDate
from django.utils import timezone
import json
from datetime import timedelta
from decimal import Decimal

from apps.repairs.models import Repair, Client


def _calc_revenue(repairs_qs):
    total = Decimal('0')
    for r in repairs_qs.prefetch_related('parts'):
        total += (r.labor_cost or 0) + r.parts_total()
    return float(total)


@login_required
def analytics_dashboard(request):
    now = timezone.now()
    year_ago = now - timedelta(days=365)

    status_data = list(
        Repair.objects.values('status').annotate(count=Count('id')))
    status_labels_map = dict(Repair.STATUS_CHOICES)
    status_chart = {
        'labels': [status_labels_map.get(d['status'], d['status']) for d in status_data],
        'data': [d['count'] for d in status_data],
    }

    monthly_qs = (Repair.objects
                  .filter(created_at__gte=year_ago)
                  .annotate(month=TruncMonth('created_at'))
                  .values('month')
                  .annotate(count=Count('id'))
                  .order_by('month'))

    monthly_labels = [m['month'].strftime('%b %Y') for m in monthly_qs]
    monthly_counts = [m['count'] for m in monthly_qs]

    monthly_revenue = []
    for m in monthly_qs:
        month_repairs = Repair.objects.filter(
            created_at__month=m['month'].month,
            created_at__year=m['month'].year,
            status__in=['done', 'issued']
        ).prefetch_related('parts')
        rev = sum(
            float(r.labor_cost or 0) + float(r.parts_total())
            for r in month_repairs
        )
        monthly_revenue.append(round(rev, 2))

    monthly_chart = {
        'labels': monthly_labels,
        'counts': monthly_counts,
        'revenue': monthly_revenue,
    }

    masters = (User.objects
               .filter(assigned_repairs__isnull=False)
               .annotate(
                   active=Count('assigned_repairs', filter=Q(
                       assigned_repairs__status__in=[
                           'new', 'diagnosed', 'in_progress', 'waiting_parts'])),
                   done=Count('assigned_repairs', filter=Q(
                       assigned_repairs__status__in=['done', 'issued']))
               )
               .distinct())
    masters_chart = {
        'labels': [u.get_full_name() or u.username for u in masters],
        'active': [u.active for u in masters],
        'done': [u.done for u in masters],
    }

    priority_data = list(
        Repair.objects.values('priority').annotate(count=Count('id')))
    priority_labels_map = dict(Repair.PRIORITY_CHOICES)
    priority_chart = {
        'labels': [priority_labels_map.get(d['priority'], d['priority']) for d in priority_data],
        'data': [d['count'] for d in priority_data],
    }

    month_ago = now - timedelta(days=30)
    daily_qs = (Repair.objects
                .filter(created_at__gte=month_ago)
                .annotate(day=TruncDate('created_at'))
                .values('day')
                .annotate(count=Count('id'))
                .order_by('day'))
    daily_chart = {
        'labels': [d['day'].strftime('%d.%m') for d in daily_qs],
        'data': [d['count'] for d in daily_qs],
    }

    completed_repairs = Repair.objects.filter(
        status__in=['done', 'issued']).prefetch_related('parts')
    total_revenue = sum(
        float(r.labor_cost or 0) + float(r.parts_total())
        for r in completed_repairs
    )
    total_repairs = Repair.objects.count()
    completed_count = completed_repairs.count()
    avg_cost = round(total_revenue / completed_count, 2) if completed_count else 0

    context = {
        'status_chart': json.dumps(status_chart, ensure_ascii=False),
        'monthly_chart': json.dumps(monthly_chart, ensure_ascii=False),
        'masters_chart': json.dumps(masters_chart, ensure_ascii=False),
        'priority_chart': json.dumps(priority_chart, ensure_ascii=False),
        'daily_chart': json.dumps(daily_chart, ensure_ascii=False),
        'total_revenue': round(total_revenue, 2),
        'avg_cost': avg_cost,
        'total_clients': Client.objects.count(),
        'total_repairs': total_repairs,
        'completed_repairs': completed_count,
    }
    return render(request, 'analytics/dashboard.html', context)
