"""
Template tags for the students application.
"""
from django import template

from ..models import RequirementCheck, SectionRequirement

#####################################################################

register = template.Library()

#####################################################################


@register.filter
def requirement_qs(section):
    """
    Given a section object, return the corresponding 
    requirement queryset.
    """
    return SectionRequirement.objects.for_section(section)


#####################################################################


@register.filter
def requirement_list(section):
    """
    Given a section object, return the corresponding 
    requirement list as a list of slugs.
    Note that this filter also removes non-active tags
    from the list.
    
    This allows for things like:
    
    {% if 'honesty' in section|requirement_list %}
        ...
    {% endif %}
    """
    qs = requirement_qs(section)
    if qs is not None:
        return qs.filter(active=True).values_list("label", flat=True)
    return None


#####################################################################


@register.filter
def has_completed_requirement(registration, label):
    """
    Given a student registration object, return the status of the labelled 
    requirement.
    
    This allows for things like:
    
    {% student_registration|has_completed_requirement:"honesty" %}
        ...
    {% endif %}
    """
    return RequirementCheck.objects.is_complete(registration, label)


#####################################################################
