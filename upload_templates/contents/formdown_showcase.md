# Formdown form demo

Easily embed a [Formdown](https://www.formdown.net/) form within a Markdown document.
Replace the attribute values with the options from your form dashboard.

## Support request

Below is a fully functional Formdown contact form. You can interact with the
fields as-is, then replace the `data-formdown-form` value with the slug from one
of your own forms when you are ready to publish.

<formdown-form
  data-formdown-form="formdown/examples/upload"
  data-formdown-theme="system"
  data-formdown-label-style="floating"
  data-formdown-success-title="Thanks for reaching out!"
  data-formdown-success-message="We received your message and will reply soon."
  data-formdown-button-label="Send message"
  data-formdown-upload="required"
  data-formdown-upload-label="Attach supporting file"
  data-formdown-upload-max-size="15"
>
  <formdown-field data-formdown-field="name"></formdown-field>
  <formdown-field data-formdown-field="email"></formdown-field>
  <formdown-field data-formdown-field="message"></formdown-field>
</formdown-form>

<noscript>
  <p>
    Formdown forms require JavaScript to load. Enable JavaScript to interact with this
    upload-enabled example, or replace the embed with your own form slug when publishing.
  </p>
</noscript>

### Common options

- `data-formdown-theme` — switch between `light`, `dark`, or `system` themes.
- `data-formdown-label-style` — choose `floating` or `stacked` labels.
- `data-formdown-success-title` / `data-formdown-success-message` — customize the confirmation copy.
- `data-formdown-button-label` — override the submit button text.
- `data-formdown-upload` — enable file uploads (`optional`, `required`, or omit to disable).
- `data-formdown-upload-label` / `data-formdown-upload-max-size` — control the uploader text and maximum size (in MB).

> **Tip:** Viewer automatically adds the Formdown loader script to Markdown pages that
> include elements with `data-formdown-*` attributes, so the embed works without adding
> extra code.
