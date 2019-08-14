from students.models import SectionRequirement


def section_has_requirement(section, tag):
    """
    This utility function checks whether or not the given section has
    the given requirement tag.
    
    Example usage:
    
    if section_has_requirement(section, 'iclicker'):
        # ...
    """
    req = SectionRequirement.objects.for_section(section)
    if req is None:
        return False  # this section has no requirements.
    return req.has(tag)
