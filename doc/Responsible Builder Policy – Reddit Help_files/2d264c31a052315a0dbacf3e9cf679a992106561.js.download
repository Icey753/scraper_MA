document.addEventListener('DOMContentLoaded', () => {
  // If there are any error notifications below an input field, focus that field
  const notificationElm = document.querySelector('.notification-error');
  if (
    notificationElm
    && notificationElm.previousElementSibling
    && typeof notificationElm.previousElementSibling.focus === 'function'
  ) {
    notificationElm.previousElementSibling.focus();
  }
});
