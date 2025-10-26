// Simple dropdown toggle for avatar menu
(function(){
  function init(){
    const btn = document.getElementById('avatarBtn');
    const menu = document.getElementById('avatarMenu');
    if(!btn || !menu) return;

    function openMenu(){
      menu.classList.add('show');
      btn.setAttribute('aria-expanded', 'true');
    }
    function closeMenu(){
      menu.classList.remove('show');
      btn.setAttribute('aria-expanded', 'false');
    }

    btn.addEventListener('click', function(e){
      e.stopPropagation();
      if(menu.classList.contains('show')) closeMenu(); else openMenu();
    });

    // close when clicking outside
    document.addEventListener('click', function(e){
      if(!menu.classList.contains('show')) return;
      if(!menu.contains(e.target) && e.target !== btn) closeMenu();
    });

    // close on escape
    document.addEventListener('keydown', function(e){ if(e.key === 'Escape') closeMenu(); });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    // DOM already ready
    init();
  }
})();
