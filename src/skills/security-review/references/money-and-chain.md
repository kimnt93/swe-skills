# Money, payment, wallet and chain code

Where it applies, [money path](../../principles/references/money-path.md) binds too: row `hard`, a replay, a human's
approval to merge.

## What to look for

- **Money:** a price, amount or fee taken from the client; floats; negative, zero or huge amounts; a balance read and
  then written in two steps (two requests spend it twice); a retry or redelivery that pays again; no limit or stop
  switch; a payment webhook trusted without its signature over the raw body, a time window and a duplicate check.
- **Wallet and chain:** a private key or seed in code, logs, a client or a model prompt; signing a transaction or
  message this code did not build or fully decode; recipient, amount, token, chain id, contract, method, fee, slippage
  or deadline unchecked; an unlimited token approval; a signed sign-in message with no domain, chain id, nonce and
  expiry (it can be replayed); success before finality; in contracts, outside calls before state changes, a missing
  caller check, `tx.origin`.

## Bad

```ts
const tx = Transaction.from(Buffer.from(req.body.tx, "base64"));
await wallet.signTransaction(tx); // signs whatever the caller sends
```

## Good

```ts
const intent = parseIntent(req.body); // recipient from the allow-list, amount within the limit
await limits.reserve(intent.id, intent); // once per intent id, atomic
const tx = buildTransfer(intent);        // the server builds what it signs
await simulate(tx);                      // the effects equal the intent, else stop
await wallet.signTransaction(tx);
```

## Prove it

On a local chain or fake broker with made-up keys: send another recipient, a larger amount, another chain id; send
the same request and webhook twice and two at once. Expected: refused, or one effect. Replay money paths
([replay test](../../replay-test/SKILL.md)). **Never mainnet, a real account, a real key or real funds.**
