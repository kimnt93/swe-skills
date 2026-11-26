# Secrets

## What to look for

Keys, tokens, passwords, private keys or seed phrases in code, tests, fixtures, config, CI, images and documents; a
default password that works when the setting is missing; a secret in a URL, a command line, a log, an error or a
Docker `ARG` or `ENV`; a secret in a browser bundle (any variable the frontend build makes public); a committed
`.env`; secrets compared with `==`.

## Bad

```go
token := os.Getenv("SERVICE_TOKEN")
if token == "" {
    token = "dev-token" // a known password in production when the variable is missing
}
```

## Good

```go
token := os.Getenv("SERVICE_TOKEN")
if token == "" {
    return fmt.Errorf("SERVICE_TOKEN is required")
}
ok := subtle.ConstantTimeCompare([]byte(got), []byte(token)) == 1
```

## Prove it

- The scan gives file and line; it never prints the value, and neither do you.
- Start the service without the variable: it must refuse to start. With the old default as the token, a local request
  must get 401.
- A browser bundle: build it with a made-up marker as the secret and count the files that hold it
  (`grep -rl <marker> <build dir> | wc -l` must print 0).

**A real secret that reached a branch is spent**, also when a later commit removes it: `Blocking`, and a person
rotates it. Never test whether it works.
