# -*- coding: utf-8 -*-
### BEGIN COPYRIGHT ###
#
# (C) Copyright 2011, Centre for Comparative Genomics, Murdoch University.
# All rights reserved.
#
# This product includes software developed at the Centre for Comparative Genomics 
# (http://ccg.murdoch.edu.au/).
# 
# TO THE EXTENT PERMITTED BY APPLICABLE LAWS, YABI IS PROVIDED TO YOU "AS IS," 
# WITHOUT WARRANTY. THERE IS NO WARRANTY FOR YABI, EITHER EXPRESSED OR IMPLIED, 
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND 
# FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT OF THIRD PARTY RIGHTS. 
# THE ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF YABI IS WITH YOU.  SHOULD 
# YABI PROVE DEFECTIVE, YOU ASSUME THE COST OF ALL NECESSARY SERVICING, REPAIR
# OR CORRECTION.
# 
# TO THE EXTENT PERMITTED BY APPLICABLE LAWS, OR AS OTHERWISE AGREED TO IN 
# WRITING NO COPYRIGHT HOLDER IN YABI, OR ANY OTHER PARTY WHO MAY MODIFY AND/OR 
# REDISTRIBUTE YABI AS PERMITTED IN WRITING, BE LIABLE TO YOU FOR DAMAGES, INCLUDING 
# ANY GENERAL, SPECIAL, INCIDENTAL OR CONSEQUENTIAL DAMAGES ARISING OUT OF THE 
# USE OR INABILITY TO USE YABI (INCLUDING BUT NOT LIMITED TO LOSS OF DATA OR 
# DATA BEING RENDERED INACCURATE OR LOSSES SUSTAINED BY YOU OR THIRD PARTIES 
# OR A FAILURE OF YABI TO OPERATE WITH ANY OTHER PROGRAMS), EVEN IF SUCH HOLDER 
# OR OTHER PARTY HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.
# 
### END COPYRIGHT ###
# -*- coding: utf-8 -*-
from yabiadmin.yabi.models import *
from yabiadmin.yabi.forms import *
from django.contrib import admin
from django.contrib.webservices.ext import ExtJsonInterface
from django.forms.models import BaseInlineFormSet
from django.forms import ModelForm
from django import forms
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseRedirect, HttpResponseServerError 
from django.utils import webhelpers 

class AdminBase(ExtJsonInterface, admin.ModelAdmin):
    save_as = True

    def save_model(self, request, obj, form, change):
        if not isinstance(obj, Base): 
            return form.save()

        instance = form.save(commit=False)
        if not change:
            instance.created_by = request.user
        instance.last_modified_by = request.user
        instance.save()
        form.save_m2m()
        return instance

    def save_formset(self, request, form, formset, change):
        if not issubclass(formset.model, Base):
            return formset.save()

        def set_user(instance):
            if instance.pk is None:
                instance.created_by = request.user
            instance.last_modified_by = request.user
            instance.save()

        instances = formset.save(commit=False)
        map(set_user, instances)
        formset.save_m2m()
        return instances

class ToolGroupingInline(admin.TabularInline):
    model = ToolGrouping
    extra = 1

class ToolOutputExtensionInline(admin.TabularInline):
    model = ToolOutputExtension
    extra = 1
    fields = ['file_extension']


class ToolParameterFormset(BaseInlineFormSet):

    def get_queryset(self):
        return super(ToolParameterFormset, self).get_queryset().order_by('id')

    def add_fields(self, form, index):
        super(ToolParameterFormset, self).add_fields(form, index)

class ToolParameterInline(admin.StackedInline):
    form = ToolParameterForm
    model = ToolParameter
    formset = ToolParameterFormset
    extra = 3

class ToolAdmin(AdminBase):
    form = ToolForm
    list_display = ['name', 'display_name', 'path', 'enabled', 'backend', 'fs_backend', 'tool_groups_str', 'tool_link', 'created_by', 'created_on']
    inlines = [ToolOutputExtensionInline, ToolParameterInline] # TODO need to add back in tool groupings and find out why it is not working with mango
    search_fields = ['name', 'display_name', 'path']
    save_as = False
    
    def get_form(self, request, obj=None, **kwargs):
        return ToolForm

class ToolGroupAdmin(AdminBase):
    list_display = ['name', 'tools_str']
    inlines = [ToolGroupingInline]
    save_as = False
    
class ToolSetAdmin(AdminBase):
    list_display = ['name', 'users_str']

class FileTypeAdmin(AdminBase):
    list_display = ['name', 'file_extensions_text']
    search_fields = ['name']    

class FileExtensionAdmin(AdminBase):
    list_display = ['pattern']
    search_fields = ['pattern']

class QueueAdmin(admin.ModelAdmin):
    list_display = ['name', 'user_name', 'created_on']

class CredentialAdmin(AdminBase):
    list_display = ['description', 'user', 'username', 'encrypted', 'is_cached','encrypt_on_login']
    list_filter = ['user']
    actions = ['encrypt_credential','decrypt_credential','cache_credential','decache_credential','set_encrypt_on_login']

    def encrypt_credential(self, request, queryset):
        selected = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)
        return HttpResponseRedirect(webhelpers.url("/ws/password_collection/?ids=%s&action=encrypt" % (",".join(selected)))) 
        
    encrypt_credential.short_description = "Encrypt selected credentials."

    def decrypt_credential(self, request, queryset):
        selected = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)        
        return HttpResponseRedirect(webhelpers.url("/ws/password_collection/?ids=%s&action=decrypt" % (",".join(selected)))) 
        
    decrypt_credential.short_description = "Decrypt selected credentials."
    
    def cache_credential(self, request, queryset):
        selected = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)        
        return HttpResponseRedirect(webhelpers.url("/ws/password_collection/?ids=%s&action=cache" % (",".join(selected)))) 
    
    cache_credential.short_description = "Cache selected credentials in decrypted form."
    
    def decache_credential(self, request, queryset):
        success,fail = 0,0
        for credential in queryset:
            if credential.is_memcached():
                credential.clear_memcache()
                success += 1
            else:
                fail += 1
                
        self.message_user(request, "%d credential%s successfully purged from cache." % (success,"s" if success!=1 else "") )
        if fail:
            self.message_user(request, "%d credential%s failed purge." % (fail,"s" if fail!=1 else "") )
        
    
    decache_credential.short_description = "Purge selected credentials from cache."
    
    def set_encrypt_on_login(self,request,queryset):
        queryset.update(encrypt_on_login=True)
        self.message_user(request, "%d credential%s successfully set to encrypt on login." % (len(queryset),"s" if len(queryset)==1 else "") )
    set_encrypt_on_login.short_description = "Encrypt on login."
    
    
    
class BackendAdmin(AdminBase):
    form = BackendForm
    list_display = ['name', 'description', 'scheme', 'hostname', 'port', 'path', 'uri', 'backend_summary_link']

class UserAdmin(AdminBase):
    list_display = ['name', 'toolsets_str', 'tools_link', 'backends_link']

class BackendCredentialAdmin(AdminBase):
    form = BackendCredentialForm
    list_display = ['backend', 'credential', 'homedir', 'visible', 'default_stageout']
    list_filter = ['credential__user']
    
class ParameterSwitchUseAdmin(AdminBase):
    list_display = ['display_text', 'formatstring', 'description']
    search_fields = ['display_text', 'description']

def register(site):
    site.register(FileExtension, FileExtensionAdmin)
    site.register(ParameterSwitchUse, ParameterSwitchUseAdmin)
    #site.register(QueuedWorkflow, QueueAdmin)
    #site.register(InProgressWorkflow, QueueAdmin)
    site.register(FileType, FileTypeAdmin)
    site.register(Tool, ToolAdmin)
    site.register(ToolGroup, ToolGroupAdmin)
    site.register(ToolSet, ToolSetAdmin)
    site.register(User, UserAdmin)
    site.register(Credential, CredentialAdmin)
    site.register(BackendCredential, BackendCredentialAdmin)
    site.register(Backend, BackendAdmin)