document.addEventListener('DOMContentLoaded', () => {
  const menus = document.querySelectorAll('.rb-chain-menu');

  const closeMenu = (menu) => {
    menu.classList.remove('is-open');
    menu.querySelector('.rb-chain-trigger')?.setAttribute('aria-expanded', 'false');
  };

  menus.forEach((menu) => {
    const trigger = menu.querySelector('.rb-chain-trigger');
    if (!trigger) return;

    trigger.addEventListener('click', (event) => {
      event.stopPropagation();
      const willOpen = !menu.classList.contains('is-open');
      menus.forEach(closeMenu);
      menu.classList.toggle('is-open', willOpen);
      trigger.setAttribute('aria-expanded', String(willOpen));
    });

    menu.querySelectorAll('.rb-cs').forEach((link) => {
      link.addEventListener('click', () => closeMenu(menu));
    });
  });

  document.addEventListener('click', () => menus.forEach(closeMenu));
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') menus.forEach(closeMenu);
  });
});
