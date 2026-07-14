document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("iframe.lw-widget").forEach((frame) => {
    const resize = () => {
      try {
        frame.style.height = `${frame.contentWindow.document.documentElement.scrollHeight}px`;
      } catch (e) {
        // cross-origin; leave whatever height is set
      }
    };

    frame.addEventListener("load", () => {
      resize();
      // widgets with sliders/animations can change height after load; poll briefly
      let tries = 0;
      const iv = setInterval(() => {
        resize();
        if (++tries > 20) clearInterval(iv);
      }, 250);
    });
  });
});
