from __future__ import unicode_literals

import collections

##########################################################################


class SingleFKBaseMixin(object):
    """
    When only a *single* foreign key option is available, use it to
    pre-populate some defaults.
    
    Because of the calling sequence, this will only work
    for fields that occur *after* the model choice field.
    
    When combining this mixin with the RestrictedAdminMixin,
    put this one before RestrictedAdminMixin in the list of parents.
    """

    single_fk_src = "<set this>"  # this is what is used for initializing.
    single_fk_initial = {
        #             'fieldname': 'fk_attr or callable(fk)'
    }

    def __init__(self, *args, **kwargs):
        """
        Set the _single_fk attribute.  If this is not None, then
        enable the processing for single foreign key initial data.
        """
        result = super(SingleFKBaseMixin, self).__init__(*args, **kwargs)
        self._single_fk = None
        return result

    def _resolve_initial_value(self, key):
        """
        Returns None when this key cannot be resolved to an initial value.
        """
        if self._single_fk is not None and key in self.single_fk_initial:
            initial = self.single_fk_initial[key]
            if isinstance(initial, collections.Callable):
                initial = initial(self._single_fk)
            elif hasattr(self._single_fk, initial):
                initial = getattr(self._single_fk, initial)
            return initial


##########################################################################


class SingleFKAdminMixin(SingleFKBaseMixin):
    """
    Because of the calling sequence, this will only work
    for fields that occur *after* the model choice field.
    
    When combining this mixin with the RestrictedAdminMixin,
    put this one before RestrictedAdminMixin in the list of parents.
    (Restrict before detecting if this is a single foreign key.)
    """

    def formfield_for_dbfield(self, db_field, **kwargs):
        """
        Modify formfields if necessary.
        """
        field = super(SingleFKAdminMixin, self).formfield_for_dbfield(
            db_field, **kwargs
        )
        # Capture the _single_fk:
        if db_field.name == self.single_fk_src:
            if field.queryset.count() == 1:
                self._single_fk = field.queryset.get()
            if "initial" not in kwargs:
                kwargs["initial"] = self._single_fk
                field = super(SingleFKAdminMixin, self).formfield_for_dbfield(
                    db_field, **kwargs
                )
        # Give initial data to fields:
        if "initial" not in kwargs:
            initial = self._resolve_initial_value(db_field.name)
            if initial is not None:
                kwargs["initial"] = initial
                field = super(SingleFKAdminMixin, self).formfield_for_dbfield(
                    db_field, **kwargs
                )
        return field


##########################################################################


class SingleFKFormViewMixin(SingleFKBaseMixin):
    """
    When combining this mixin with the RestrictedAdminMixin,
    put this one before RestrictedAdminMixin in the list of parents.
    (Restrict before detecting if this is a single foreign key.)
    """

    def get_form(self, *args, **kwargs):
        form = super(SingleFKFormViewMixin, self).get_form(*args, **kwargs)
        for f in form.fields:
            if f == self.single_fk_src:
                if form.fields[f].queryset.count() == 1:
                    self._single_fk = form.fields[f].queryset.get()
                    form.fields[f].initial = self._single_fk
            # handle single value fk.
            if form.fields[f].initial is None:
                form.fields[f].initial = self._resolve_initial_value(f)

        return form


##########################################################################
