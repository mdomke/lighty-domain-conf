Lighttpd Domain Configuration
=============================

This simple script is intended for managing domain-configurations of a
[lighttpd](http://lighttpd.net)-webserver.

Setup
-----

To get started you have to adjust the `LIGHTTPD_CONF_DIR`-variable at
the top of the script to the directory where your lighttpd configuration
files should be created. The default is `/etc/lighttpd`.

To initialize the directory structure for the domain-configuration files
type:

    ./lighty-domain-config.py --init

This will create the file `incl-domains.conf` where all include-directives
are put in as well as the `domains`-subdirectory where the actual domain-configuration
files will be located. You have to add the following line to your `lighttpd.conf`
file so that your configuration files will be honored:

    include "/path/to/incl-domains.conf

Usage
-----

### Adding domains

To add new domain-configuration file to your setup invoke the following command:

    ./lighty-domain-config.py --add your_domain.tld

This will create a new file `your_domain.tld.conf` in the `domains`-subdirectory
and add a corresponding include-directive to the `incl-domain.conf`-file. 

### Removing domains

To remove a domain from the setup and delete its configuration-file use:

    ./lighty-domain-config.py --remove your_domain.tld

It is also possible to only exclude the file from the configuration without deleting
the file by using the `--exclude|-e` paramter.
