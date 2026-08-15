from .models import Membership


def company_context(request):
    if not request.user.is_authenticated:
        return {}
    memberships = Membership.objects.select_related("company").filter(
        user=request.user, active=True, company__active=True,
    )
    selected_id = request.session.get("minefleet_company_id")
    membership = memberships.filter(company_id=selected_id).first() if selected_id else memberships.first()
    return {"membership": membership, "memberships": memberships}
