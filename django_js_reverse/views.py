# coding: utf-8
import re
import sys
from itertools import chain
from django.http import HttpResponse

if sys.version < '3':
    text_type = basestring
else:
    text_type = str

from django.core.exceptions import ImproperlyConfigured
from django.template import loader
from django.core import urlresolvers
from django.conf import settings
from django import get_version

from slimit import minify
from .js_reverse_settings import (JS_VAR_NAME, JS_MINIFY,
                                  JS_EXCLUDE_NAMESPACES, JS_EXCLUDE_URLNAMES)


content_type_keyword_name = 'content_type'
if get_version() < '1.5':
    content_type_keyword_name = 'mimetype'


JS_EXCLUDE_NAMESPACES = getattr(settings, 'JS_REVERSE_EXCLUDE_NAMESPACES',
                                JS_EXCLUDE_NAMESPACES)

JS_EXCLUDE_URLNAMES = getattr(settings, 'JS_REVERSE_EXCLUDE_URLNAMES',
                              JS_EXCLUDE_URLNAMES)


def urls_js(request=None):
    js_var_name = getattr(settings, 'JS_REVERSE_JS_VAR_NAME', JS_VAR_NAME)
    if not re.match(r'^[$A-Z_][\dA-Z_$]*$', js_var_name.upper()):
        raise ImproperlyConfigured(
            'JS_REVERSE_JS_VAR_NAME setting "%s" is not a valid javascript identifier.' % (js_var_name))

    minfiy = getattr(settings, 'JS_REVERSE_JS_MINIFY', JS_MINIFY)
    if not isinstance(minfiy, bool):
        raise ImproperlyConfigured(
            'JS_REVERSE_JS_MINIFY setting "%s" is not a valid. Needs to be set to True or False.' % (minfiy))

    default_urlresolver = urlresolvers.get_resolver(getattr(request, 'urlconf', None))

    named_urlresolves = [
        (n_urlresolver, namespace_path, namespace + ':')
        for namespace, (namespace_path, n_urlresolver) in default_urlresolver.namespace_dict.items()
    ]
    url_lists = [prepare_url_list(*args) for args in named_urlresolves]

    # add urls without namespaces
    url_lists.append((prepare_url_list(default_urlresolver)))

    response_body = loader.render_to_string(
        'django_js_reverse/urls_js.tpl',
        {
            'urls': chain(*url_lists),
            'url_prefix': urlresolvers.get_script_prefix(),
            'js_var_name': js_var_name
        },
        {})
    if minfiy:
        response_body = minify(response_body, mangle=True, mangle_toplevel=False)

    if not request:
        return response_body
    else:
        return HttpResponse(response_body, **{content_type_keyword_name: 'application/javascript'})


def prepare_url_list(urlresolver, namespace_path='', namespace=''):
    """
    returns list of tuples [(<url_name>, <namespace_path>, <url_patern_tuple> ), ...]
    """
    for url_name, url_pattern in urlresolver.reverse_dict.items():
        if not isinstance(url_name, text_type):
            continue

        if JS_EXCLUDE_NAMESPACES and namespace[:-1] in JS_EXCLUDE_NAMESPACES:
            continue

        if JS_EXCLUDE_URLNAMES and url_name in JS_EXCLUDE_URLNAMES:
            continue

        yield [namespace + url_name, namespace_path, url_pattern[0][0]]
