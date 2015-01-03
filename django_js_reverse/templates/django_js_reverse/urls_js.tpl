this.{{ js_var_name }} = (function () {
    var config = {
        'use_subdomains': {{ JS_USE_SUBDOMAIN }},
        'urls': {{ urls|safe }},
        'domains': {{ domains|safe }},
        'url_prefix': '{{ url_prefix|escapejs }}'},
        Urls = {};

    Urls.get = function (name, subdomain) {
        var domain;

        if (config.use_subdomains && subdomain) {
            domain = subdomain + '.' + location.host;
        } else {
            domain = location.host
        }

        return get_url(domain, name);
    }

    function get_url (domain, name) {
        var urls = config['urls'],
            rule = urls[config.use_subdomains ? domain : 'null'][name];

        if (!rule) {
            throw 'Unknow url name: ' + name;
        }

        return function () {
            var url_args = rule[1],
                url = rule[0],
                url_arg, index, _i, _len;

            for (index = _i = 0, _len = url_args.length; _i < _len; index = ++_i) {
                url_arg = url_args[index];
                url = url.replace("%(" + url_arg + ")s", arguments[index] || '');
            }

            if (config.use_subdomains && domain !== location.host) {
                return 'http://' + domain + config.url_prefix + url;
            }

            return config.url_prefix + url;
        }
    }

    return Urls;
})();
