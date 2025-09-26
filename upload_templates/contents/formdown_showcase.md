# Formdown form demo

Easily embed a [Formdown](https://formdown.dev/) form within a Markdown document.
Replace the attribute values with the options from your workspace dashboard.

## Support request

Below is a working Formdown.dev script that demonstrates the updated DSL syntax.
Publish this template as-is to try it out, then swap in the copy that matches
your own workflow.

```formdown
Share a support request along with any screenshots that help explain the issue.

[[
--Your name--
T___firstName
#placeholder|First name
{r m2 M40}

T___lastName
#placeholder|Last name
{r m2 M40}
]]

--Email address--
@___email
#helper|We'll use this address to follow up.
{r}

--Issue summary--
T=__summary
#type|textarea
#helper|Provide as much detail as you can.
{r m10 M400}

--Attach a supporting file--
U___supportingFile
#helper|Optional upload, max 15 MB.
{M15}

(submit|Send request)
```

### Common options

- Prefix inputs with `T___`, `@___`, `U___`, or `*___` to render text, email,
  upload, and password fields respectively.
- Use `{r}` to make a field required, `m` and `M` to set minimum and maximum
  lengths, and `#helper|` or `#placeholder|` to add guidance for users.
- Wrap fields inside `[[ ... ]]` blocks to group them so Formdown renders them
  side-by-side on larger screens.

> **Tip:** Viewer automatically converts ` ```formdown` fences into live embeds
> and appends the Formdown.dev loader script, so the published page renders the
> interactive form rather than a static code sample.
