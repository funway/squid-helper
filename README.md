# squid-helper
Some external helper for squid 3.4+.

### digest_redis_auth

Digest authentication helper for squid 3.4+.

 - It get a line input from squid by sys.stdin,  
 - Then fetch the auth info from **redis-server**,  
 - And finally send the info back to squid by sys.stdout.

###### input and output
- Input line from squid:
`"username":"realm" [key-extras]`
- Output line send back to squid:
    `OK ha1="xxx"`
    or `ERR message="xxx"`
    or `BH message="xxx"`
- key-value in redis:
    `realm:username ==> ha1`

###### Usage in squid.conf
`auth_param digest program /path_to/digest_redis_auth.py -f /path_to/logfile.log -l DEBUG`

### redis_login_ip_acl
