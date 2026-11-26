# Session and browser attacks

## What to look for

| Attack | Look for |
|---|---|
| script injection (XSS) | raw HTML from data, `javascript:` links, a markdown or HTML renderer with no allow-list sanitizer, a weaker content security policy |
| cross-site request (CSRF) | cookie sign-in with a state change that needs no token or origin check, or that a `GET` performs |
| cookies and sessions | no `HttpOnly`, `Secure` or `SameSite`; a wide `Domain`; no expiry; the same session id after sign-in; sign-out that leaves the session valid; tokens in browser storage |
| CORS | `*`, an origin echoed back, a suffix match, credentials allowed with any of these |
| redirect, framing, messages | a redirect target from input; no `frame-ancestors`; `postMessage` with no origin check |

## Bad

```ts
const next = new URL(location.href).searchParams.get("next")!;
location.assign(next); // sends the signed-in user anywhere, or runs a javascript: URL
preview.innerHTML = user.bio;
```

## Good

```ts
const next = new URL(location.href).searchParams.get("next") ?? "/";
const target = new URL(next, location.origin);
location.assign(target.origin === location.origin ? target.pathname + target.search : "/");
preview.textContent = user.bio;
```

## Prove it

On a local instance: save a profile with `<img src=x onerror="window.__xss=1">` and assert in a real browser that it
shows as text and `window.__xss` is unset; open the redirect with `//other.test` and `javascript:` and stay on the
origin; send the state change from another origin without the token and get 403; read the `Set-Cookie` and CORS
headers of the real response.
