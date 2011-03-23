#!/usr/bin/env python

from __future__ import with_statement
from __future__ import print_function

import os
import yaml

from optparse import OptionParser

LIGHTTPD_CONF_DIR = "/etc/lighttpd"

config_data = """
files: 
    doc-root:  incl-doc-root.conf
    domains:   incl-domains.conf
    django:    incl-django-fastcgi.conf
    wordpress: incl-wordpress.conf

templates:
    doc-root: >
        server.document-root = basename + servername + "/pages"

    vhost: |
        var.basename = /var/www/
        $HTTP["host"] =~ "^(www\.)?<domainname>$" {
            var.servername = "<domainname>"
            <includes>
        }

    django: |
        fastcgi.server = (
            "/django.fcgi" => (
                "main" => (
                    "socket" => "/var/local/django/" + servername + ".sock",
                    "check-local" => "disable",
                )
            ),
        )

        alias.url = (
            "/media/" => "/var/local/django/contrib/admin/media/",
        )

        url.rewrite-once = (
            "^(/media.*)$" => "$1",
            "^/favicon\.ico$" => "/media/favicon.ico",
            "^(/.*)$" => "/django.fcgi$1",
        )        

    wordpress: |
        server.error-handler-404 = "/index.php"
        url.rewrite-once = (
            "^/(.*/)?files/$" => "/index.php",
            "^/(.*/)?files/(.*)" => "/wp-content/blogs.php?file=$2",
            "^(/wp-admin/.*)" => "$1",
            "^/([_0-9a-zA-Z-]+/)?(wp-.*)" => "/$2",
            "^/([_0-9a-zA-Z-]+/)?(.*\.php)$" => "/$2",
        )
"""

class LighttpdConfEditor(object):
    def __init__(self, domains, config):
        super(LighttpdConfEditor, self).__init__()
        self.domains = domains
        self.conf_dir = config.conf_dir
        self.verbose = config.verbose
        self.remove = config.remove_config
        self.exclude = config.exclude_config
        self.output_prefix = "-->"
        self.error_prefix = "***"

        self.include_modules = ["doc-root"]

        if config.include_modules:
            self.include_modules.extend(
                [mod.strip() for mod in config.include_modules.split(",")]
            )

        self.config_data = yaml.load(config_data)


    def init_domain_dir(self):

        domain_config_dir = os.path.join(self.conf_dir, "domains")
        if not os.path.exists(domain_config_dir):
            os.makedirs(domain_config_dir)

        for template_name in self.config_data['files']:
            template_path = os.path.join(domain_config_dir,
                                         self.config_data['files'][template_name])

            with open(template_path, 'w+') as template_file:
                try:
                    template = self.config_data['templates'][template_name]
                    template_file.write(template)
                    if self.verbose:
                        print(self.output_prefix, 
                              "Writing template for module '{0}'".format(template_name))
                except KeyError:
                    pass


    def update_config(self):
        """
        Update the lighttpd configuration file that holds
        the inlcude-statements for the virtual hosts
        """

        if self.verbose:
            print("# Lighttpd conf-dir = '{0}'".format(LIGHTTPD_CONF_DIR))

        conf_file_path = os.path.join(self.conf_dir, 
                                      self.config_data['files']['domains'])

        with open(conf_file_path, 'w+') as conf_file:
            rewrite_config = False
            tmp_buffer = [l.strip(" \n") for l in conf_file.readlines()]

            for domain in self.domains:
                include_line = 'include "{0}.conf"'.format(os.path.join("domains", domain))

                if self.remove or self.exclude:
                    if include_line in tmp_buffer:
                        if self.verbose:
                            print(self.output_prefix, 
                                  "Excluding domain '{0}' from '{1}'".format(
                                      domain, self.config_data['files']['domains']))
                        tmp_buffer.remove(include_line)
                        rewrite_config = True

                    if self.remove:
                        incl_conf_path = os.path.join(self.conf_dir, 
                                                      "domains", 
                                                      "{0}.conf".format(domain))

                        if os.path.exists(incl_conf_path):
                            os.remove(incl_conf_path)
                            if self.verbose:
                                print(self.output_prefix, 
                                      "Removing 'domains/{0}.conf'".format(domain))

                else:
                    if not include_line in tmp_buffer:
                        if self.verbose:
                            print(self.output_prefix, 
                                  "Adding domain '{0}' to '{1}'".format(
                                      domain, self.config_data['files']['domains']))

                        tmp_buffer.append(include_line)
                        self.create_config_prototype(domain)
                        rewrite_config = True

            if rewrite_config:
                conf_file.seek(0)
                conf_file.truncate()
                conf_file.write("\n".join(tmp_buffer))

    def create_config_prototype(self, domain):

        config_file_path = os.path.join(self.conf_dir, "domains", "{0}.conf".format(domain))

        if not os.path.exists(config_file_path):

            # Read the configuration template-file if it exists. If not
            # use the simple configuration snippet from above.
            template_path = os.path.join(self.conf_dir, "domains", "vhost.skel")
            template = ""
            if os.path.exists(template_path):
                with open(template_path, 'r') as template_file:
                    template = "".join(template_file.readlines())
            else:
                template = self.config_data['templates']['vhost']

            # Fill in the domain-name
            template = template.replace("<domainname>", domain)

            include_lines = []
            for module in self.include_modules:
                try:
                    include_lines.append(self.config_data['files'][module])
                except KeyError:
                    pass

            template = template.replace("<includes>", "\n    ".join(include_lines))

            with open(config_file_path, 'w') as config_file:
                if self.verbose:
                    print(self.output_prefix, 
                          "Creating 'domains/{0}.conf'".format(domain))

                config_file.write(template)

        else:
            if self.verbose:
                print(self.output_prefix, 
                      "Config-file '{0}.conf' already exists".format(domain))
        

if __name__ == '__main__':
    usage = "%prog [-d confdir] (--add|--remove|--exclude) domainname"
    parser = OptionParser(usage)

    parser.add_option("-d", "--dir", dest="conf_dir", 
                      default=LIGHTTPD_CONF_DIR,
                      help="Lighttpd configuration directory [{0}]".format(LIGHTTPD_CONF_DIR))

    parser.add_option("-a", "--add", action="store_false", dest="remove_config",
                     help="Add domainname to configuration")

    parser.add_option("-r", "--remove", action="store_true", dest="remove_config",
                     help="Remove domainname from configuration")

    parser.add_option("-e", "--exclude", action="store_true", dest="exclude_config",
                     help="Exclude domainname (temporarily) from configuration")

    parser.add_option("-q", "--quiet", action="store_false", default=True, dest="verbose",
                     help="Suppress output")

    parser.add_option("-i", "--init", action="store_true", default=False, dest="init_domain_dir",
                     help="Initialize the config-directory strucutre")

    parser.add_option("-m", "--modules", dest="include_modules", 
                      help="Available modules: vhost, django, wordpress")

    (options, args) = parser.parse_args()

    if not options.init_domain_dir:
        if options.remove_config == None and options.exclude_config == None:
            parser.error("Please specify an action with the --add/--remove/--exclude options")

        if options.remove_config == False and options.exclude_config:
            parser.error("The options --add and --exclude are mutually exclusive")

        if len(args) == 0:
            parser.error("Please specify a domainname to be added")

    if not os.path.exists(options.conf_dir):
        parser.error("""The config dir '{0}' does not exist. You probably hav to modify
                     the LIGHTTPD_CONF_DIR variable of this script.""".format(options.conf_dir))

    config_editor = LighttpdConfEditor(args, options)

    if options.init_domain_dir:
        config_editor.init_domain_dir()
    else:
        config_editor.update_config()


