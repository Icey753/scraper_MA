(function ($, window, document) {
  const TOGGLE_ELEMENT = '[data-category-accordion-toggle]';

  const CategoryAccordion = {
    init() {
      this.cacheElements();
      this.bindEvents();
    },
    cacheElements() {
      this.$button = $(TOGGLE_ELEMENT);
    },
    bindEvents() {
      $(document).on('click', TOGGLE_ELEMENT, this.handleClick);
    },
    handleClick(e) {
      e.preventDefault();
      const $title = $(e.target);
      const isExpanded = $title.attr('aria-expanded') === 'true';
      $title.toggleClass('lt-category-accordion__link--active');
      $title
        .attr('aria-expanded', !isExpanded)
        .parents('[data-category-accordion]')
        .find('[data-category-accordion-content]')
        .slideToggle();
    },
  };

  $(() => {
    CategoryAccordion.init();
  });
}(jQuery, window, document));
