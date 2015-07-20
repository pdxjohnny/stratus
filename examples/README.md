Stratus Examples
---

This will show you how to create a service quickly with stratus.

In one shell you can start the service
```bash
$ nodemon -e py --exec "python -m examples.service localhost"
```
I use nodemon here so that you can change the methods in the the service
class without manually restarting your client program


Then in another terminal you can run the client command line interface
```bash
$ python -m examples.cli localhost
Method to call: db say_hello user
Hello user
Method to call:
```
Leave this program running and edit the examples/service.py file say_hello
method

```python
class service(stratus.stratus):

    def say_hello(self, name):
        return "Hello " + str(name)
```
To anything
```python
class service(stratus.stratus):

    def say_hello(self, name):
        return "Hello there" + str(name)
```

Jump back to your cli client shell and call the method again
```bash
$ python -m examples.cli localhost
Method to call: db say_hello user
Hello user
Method to call: db say_hello user
Hello there user
```

Congratulations you've just created your first microservice with stratus!

Next steps:
---
1. Create another service
  1. Copy paste the service class
  2. Rename it
  3. Copy paste the loop where the original service was created
  4. Make `to_launch = your_new_service_name()`
  5. In `to_launch.connect()` make sure `service=name_of_your_service`
  6. Call it from your cli shell: `name_of_your_service say_hello user`
2. Launch multiple services
  1. Change `NUM_SERVICES = how ever many you want`
  2. Don't go crazy I'm still working on this project
3. Launch services on other computers
  1. Copy over the stratus repo you've modified or clone it again
  2. Add some prints to the service methods to see which machine they are
    being called on
  3. Instead of launching examples.service as
    `python -m examples.service localhost` substitute the ip of the machine from your first
    setup for localhost
    `python -m examples.service <ip of first machine>`
