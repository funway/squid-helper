# digest_redis_auth

Digest authentication helper for squid 3.4+.

 - It get a line input from squid by sys.stdin,  
 - Then fetch the auth info from **redis-server**,  
 - And finally send the info back to squid by sys.stdout.

### Version
0.1.1

- Input line from squid:
`"username":"realm" [key-extras]`
- Output line send back to squid:
    `OK ha1="xxx"`
    or `ERR message="xxx"`
    or `BH message="xxx"`
- key-value in redis:
    `realm:username ==> ha1`
