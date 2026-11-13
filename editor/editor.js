'use strict';

const form = document.querySelector('#editor');
const status = document.querySelector('#status');
const next = document.querySelector('#next');
const submission = document.querySelector('#submission');
const language = document.querySelector('#language');
const image = document.querySelector('#preview-image');
const draftKey = 'globewire-editor-draft-v1';
let imageUrl = '';

function fields() {
  return Object.fromEntries(new FormData(form));
}

function httpsUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && !url.username && !url.password;
  } catch {
    return false;
  }
}

function preview() {
  const data = fields();
  const lang = language.value;
  document.querySelector('#preview').lang = lang;
  document.querySelector('#preview-category').textContent =
    data.category ? form.elements.category.selectedOptions[0].textContent : '';
  document.querySelector('#preview-title').textContent =
    data[lang + '_title'].trim() || 'आपका शीर्षक यहाँ दिखेगा';
  document.querySelector('#preview-body').textContent =
    data[lang + '_body'].trim() || 'लेख लिखना शुरू करें।';
  const url = data.image_url.trim();
  if (url !== imageUrl) {
    imageUrl = url;
    image.hidden = true;
    if (httpsUrl(url)) image.src = url;
    else image.removeAttribute('src');
  }
}

function invalidateSubmission() {
  next.hidden = true;
  submission.value = '';
  status.textContent = '';
}

try {
  const draft = JSON.parse(localStorage.getItem(draftKey) || '{}');
  for (const name of Object.keys(fields())) {
    if (typeof draft[name] === 'string') form.elements[name].value = draft[name];
  }
} catch {
  // Editing and publishing work with storage disabled.
}
image.addEventListener('load', () => { image.hidden = false; });
image.addEventListener('error', () => { image.hidden = true; });
form.addEventListener('input', () => {
  invalidateSubmission();
  try {
    localStorage.setItem(draftKey, JSON.stringify(fields()));
  } catch {
    status.textContent = 'इस ब्राउज़र में ड्राफ्ट सेव नहीं हो सका।';
  }
  preview();
});
language.addEventListener('change', preview);
document.querySelector('#clear').addEventListener('click', () => {
  if (!confirm('इस ब्राउज़र में सेव ड्राफ्ट हटाएँ?')) return;
  form.reset();
  try { localStorage.removeItem(draftKey); } catch { /* Storage disabled. */ }
  invalidateSubmission();
  preview();
});

function validate(data) {
  if (data.en_title.length < 5 || data.en_body.length < 150) {
    return 'English headline में कम से कम 5 और लेख में 150 अक्षर दें।';
  }
  const hindi = /[\u0900-\u097f]/;
  if ((data.hi_title || data.hi_body || data.hi_meta) &&
      (data.hi_title.length < 5 || data.hi_body.length < 150 ||
       !hindi.test(data.hi_title) || !hindi.test(data.hi_body))) {
    return 'हिंदी संस्करण के लिए हिंदी शीर्षक और कम से कम 150 अक्षर का हिंदी लेख दें।';
  }
  if (data.source && !httpsUrl(data.source)) return 'स्रोत का पूरा HTTPS लिंक दें।';
  if (data.image_upload && data.image_url) return 'अपलोड की गई फोटो का नाम या फोटो लिंक, दोनों में से एक भरें।';
  if (data.image_upload && !/^[a-z0-9][a-z0-9._ -]*\.(jpe?g|png|webp)$/i.test(data.image_upload)) {
    return 'अपलोड की गई JPG, PNG या WebP फोटो का पूरा फ़ाइल नाम भरें।';
  }
  if (data.image_url && !httpsUrl(data.image_url)) return 'फोटो का पूरा HTTPS लिंक दें।';
  if (data.image_upload || data.image_url || data.image_credit || data.image_license) {
    if (!(data.image_upload || data.image_url) || !data.image_credit || !data.image_license) {
      return 'फोटो, क्रेडिट और उपयोग की अनुमति भरें।';
    }
  }
  return '';
}

form.addEventListener('invalid', event => {
  const details = event.target.closest('details');
  if (details) details.open = true;
}, true);
form.addEventListener('submit', async event => {
  event.preventDefault();
  const data = Object.fromEntries(Object.entries(fields()).map(([key, value]) => [key, value.trim()]));
  const error = validate(data);
  if (error) {
    status.textContent = error;
    return;
  }
  const payload = JSON.stringify(data);
  if (new TextEncoder().encode(payload).length > 64000) {
    status.textContent = 'पोस्ट लंबी है। GitHub पर भेजने के लिए लेख थोड़ा छोटा करें।';
    return;
  }
  submission.value = payload;
  next.hidden = false;
  try {
    await navigator.clipboard.writeText(payload);
    status.textContent = 'पोस्ट कॉपी हो गई। अब GitHub में खोलें।';
  } catch {
    submission.focus();
    submission.select();
    status.textContent = 'चुने हुए टेक्स्ट को कॉपी करें, फिर GitHub में खोलें।';
  }
  next.scrollIntoView({ block: 'nearest' });
});
preview();
