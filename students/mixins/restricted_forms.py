from __future__ import unicode_literals

##########################################################################


class RestrictedBaseMixin(object):
    """
    Restrict non-superusers.
    """

    is_restricted_user = "<set or define this> callable: instance, user -> bool"
    restricted_user_filter = None  # fieldname for =user filtering
    restricted_exclude_fields = []  # list of fields restricted users get excluded
    restricted_foreign_key_fields = {
        #             fieldname: modelattr__rel__user
    }  # map field names to =user restriction string.
    restricted_extra_filters = {}  # set this to, e.g., {'active': True}

    def _should_restrict(self, user):
        """
        Should this user be restricted?
        """
        return not user.is_superuser and self.is_restricted_user(user)


##########################################################################


class RestrictedAdminMixin(RestrictedBaseMixin):
    """
    Used to restrict access for non-superusers in the adin
    """

    def get_queryset(self, request):
        """
        This function restricts the default queryset in the
        admin list view.
        """
        qs = super(RestrictedAdminMixin, self).get_queryset(request)
        # If super-user, show all; otherwise restrict to future by conf setting:
        if self._should_restrict(request.user):
            if self.restricted_user_filter:
                qs = qs.filter(**{self.restricted_user_filter: request.user})
            if self.restricted_extra_filters:
                qs = qs.filter(**self.restricted_extra_filters)
        return qs.distinct()

    def get_fields(self, request, obj=None):
        """
        If the user is restricted, exclude any necessary fields.
        """
        fields = super(RestrictedAdminMixin, self).get_fields(request, obj)
        if self._should_restrict(request.user):
            fields = [f for f in fields if f not in self.restricted_exclude_fields]
        return fields

    def formfield_for_dbfield(self, db_field, **kwargs):
        """
        Modify foreign key querysets to also be resticted.
        """
        request = kwargs.get("request", None)
        field = super(RestrictedAdminMixin, self).formfield_for_dbfield(
            db_field, **kwargs
        )
        if request is not None and self._should_restrict(request.user):
            if db_field.name in self.restricted_foreign_key_fields:
                fk_restrict = {
                    self.restricted_foreign_key_fields[db_field.name]: request.user
                }
                field.queryset = field.queryset.filter(**fk_restrict)
        return field

    def get_prepopulated_fields(self, request, obj=None):
        """
        Hook for specifying custom prepopulated fields.
        """
        prepop_fields = super(RestrictedAdminMixin, self).get_prepopulated_fields(
            request, obj
        )
        if self._should_restrict(request.user):
            for f in self.restricted_exclude_fields:
                if f in prepop_fields:
                    prepop_fields.pop(f)
        return prepop_fields


##########################################################################


class RestrictedFormViewMixin(RestrictedBaseMixin):
    def get_form(self, *args, **kwargs):
        """
        CBV form restrictions
        """
        form = super(RestrictedFormViewMixin, self).get_form(*args, **kwargs)
        if self._should_restrict(self.request.user):
            # exclude restricted fields...
            for f in self.restricted_exclude_fields:
                if f in form.fields:
                    form.fields.pop(f, None)
            # restrict fk options...
            for f in self.restricted_foreign_key_fields:
                if f in form.fields:
                    fk_restrict = {
                        self.restricted_foreign_key_fields[f]: self.request.user
                    }
                    form.fields[f].queryset = form.fields[f].queryset.filter(
                        **fk_restrict
                    )
                    # if restricted to one fk, preselect it:
        #                     if form.fields[f].queryset.count() == 1:
        #                         form.fields[f].initial = form.fields[f].queryset.get()

        return form


##########################################################################


class RestrictedQuerysetMixin(RestrictedBaseMixin):
    def get_queryset(self, *args, **kwargs):
        qs = super(RestrictedFormViewMixin, self).get_queryset(*args, **kwargs)
        if self._should_restrict(self.request.user):
            if self.restricted_user_filter:
                qs = qs.filter(**{self.restricted_user_filter: self.request.user})
            if self.restricted_extra_filters:
                qs = qs.filter(**self.restricted_extra_filters)
        return qs.distinct()


##########################################################################
