# Files, commands and URLs from input

## What to look for

| Use of input | Needs |
|---|---|
| a file path | a name you generate, or resolve it and require it under the base directory, symlinks included |
| an upload | size limit, type checked by content, stored outside what is served or run, a generated name |
| an archive | every entry's path checked, links refused, a limit on total size and count |
| a command | an argument list and **no shell**; `--` before values; a value that starts with `-` refused |
| stored or sent data | a data format only: never `pickle` or an unsafe YAML load |
| a URL the server fetches (**SSRF**) | allow-listed scheme and host; the resolved address not loopback, private, link-local or metadata; the same checks on **every redirect**; connect to the checked address; timeout and size limit |

## Bad

```python
subprocess.run(f"convert {name} out.png", shell=True)
return Response((BASE / name).read_bytes())          # name = "../../etc/passwd"
page = httpx.get(body.callback_url, follow_redirects=True)
```

## Good

```python
path = (BASE / name).resolve()
if not path.is_relative_to(BASE.resolve()) or name.startswith("-"):
    raise BadName(name)
subprocess.run(["convert", "--", str(path), "out.png"], check=True, timeout=30)
url = allowed_callback(body.callback_url)  # the table's checks; redirects off
```

## Prove it

Local tests with `../` and absolute names, a link that points outside, a name `-help`, a name with `;` and a marker
command (it must create nothing), an archive with `../` entries. For SSRF run a local fake server and pass its
address, and a redirect to it: the request is refused and **the fake server saw nothing**. Never aim a proof at a real
inner or cloud address.
