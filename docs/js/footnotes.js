document.addEventListener("DOMContentLoaded", () => {
  const refs = Array.from(document.querySelectorAll("main sup a[href^='#fn']"));
  if (!refs.length) return;

  const wideQuery = window.matchMedia("(min-width: 1220px)");
  const sidenotes = [];

  refs.forEach((ref, i) => {
    const li = document.getElementById(ref.getAttribute("href").slice(1));
    if (!li) return;

    const sup = ref.parentElement;
    sup.classList.add("footnote-ref-wrap");

    const clone = li.cloneNode(true);
    clone.querySelectorAll("a[href^='#fnref']").forEach((a) => a.remove());
    const noteHTML = clone.innerHTML.trim();

    // Hover/click tooltip, used on narrow viewports.
    const tooltip = document.createElement("span");
    tooltip.className = "footnote-tooltip";
    tooltip.innerHTML = noteHTML;
    sup.appendChild(tooltip);

    // Always-visible margin sidenote, used on wide viewports. Label it with
    // the number the in-text marker itself shows, not the ref's position in
    // the page, so a footnote cited twice (e.g. "4" ... "4") keeps its real
    // number both times instead of being renumbered by occurrence.
    const number = ref.textContent.trim();
    const sidenote = document.createElement("aside");
    sidenote.className = "sidenote";
    sidenote.setAttribute("aria-hidden", "true");
    sidenote.innerHTML = `<span class="sidenote-number">${number}.</span>${noteHTML}`;
    document.body.appendChild(sidenote);
    sidenotes.push({ ref, sidenote });

    let pinned = false;
    const show = () => {
      tooltip.style.left = "0";
      tooltip.classList.add("visible");
      const margin = 8;
      const rect = tooltip.getBoundingClientRect();
      let shift = 0;
      if (rect.right > window.innerWidth - margin) {
        shift = window.innerWidth - margin - rect.right;
      }
      if (rect.left + shift < margin) {
        shift = margin - rect.left;
      }
      if (shift) tooltip.style.left = `${shift}px`;
    };
    const hide = () => {
      if (!pinned) tooltip.classList.remove("visible");
    };
    const activateSidenote = () => {
      sidenote.classList.add("active");
      ref.classList.add("sidenote-active");
    };
    const deactivateSidenote = () => {
      sidenote.classList.remove("active");
      ref.classList.remove("sidenote-active");
    };

    ref.addEventListener("mouseenter", () => {
      show();
      activateSidenote();
    });
    ref.addEventListener("mouseleave", () => {
      hide();
      deactivateSidenote();
    });
    ref.addEventListener("focus", () => {
      show();
      activateSidenote();
    });
    ref.addEventListener("blur", () => {
      hide();
      deactivateSidenote();
    });
    ref.addEventListener("click", (e) => {
      e.preventDefault();
      pinned = !pinned;
      tooltip.classList.toggle("visible", pinned);
    });

    sidenote.addEventListener("mouseenter", activateSidenote);
    sidenote.addEventListener("mouseleave", deactivateSidenote);
  });

  document.addEventListener("click", (e) => {
    document.querySelectorAll(".footnote-tooltip.visible").forEach((tooltip) => {
      if (!tooltip.parentElement.contains(e.target)) {
        tooltip.classList.remove("visible");
      }
    });
  });

  // The <sup> marker is raised and shrunk (vertical-align: super, smaller
  // font-size), so its own bounding box does not sit at the top of the text
  // line it appears on. Measure the line itself via the last character of
  // the normal-size text immediately preceding the marker instead, so the
  // sidenote's top line lands level with that text line rather than
  // wherever the small raised glyph happens to sit.
  const lineTop = (ref) => {
    const sup = ref.parentElement;
    const prev = sup.previousSibling;
    if (prev && prev.nodeType === Node.TEXT_NODE && prev.textContent.length) {
      const range = document.createRange();
      range.setStart(prev, prev.textContent.length - 1);
      range.setEnd(prev, prev.textContent.length);
      const rects = range.getClientRects();
      if (rects.length) return rects[rects.length - 1].top;
    }
    return sup.getBoundingClientRect().top;
  };

  const positionSidenotes = () => {
    if (!wideQuery.matches) return;
    const bodyTop = document.body.getBoundingClientRect().top;
    const gap = 12;
    let prevBottom = -Infinity;
    sidenotes.forEach(({ ref, sidenote }) => {
      const refTop = lineTop(ref) - bodyTop;
      let top = refTop;
      if (top < prevBottom + gap) top = prevBottom + gap;
      sidenote.style.top = `${top}px`;
      prevBottom = top + sidenote.offsetHeight;
    });
  };

  // Coalesce bursts of triggers (e.g. a widget's resize-polling) into a
  // single reposition on the next animation frame, so sidenotes stay in
  // sync with layout changes instead of visibly lagging behind them
  // (which reads as "buggy" while scrolling past content as it loads).
  let rafId = null;
  const schedulePositioning = () => {
    if (rafId !== null) return;
    rafId = requestAnimationFrame(() => {
      rafId = null;
      positionSidenotes();
    });
  };

  positionSidenotes();
  window.addEventListener("load", positionSidenotes);
  window.addEventListener("resize", schedulePositioning);
  if (wideQuery.addEventListener) {
    wideQuery.addEventListener("change", positionSidenotes);
  }

  // Iframes, images, and other embeds (e.g. the interactive widgets) can
  // finish loading and change layout height well after DOMContentLoaded,
  // so reposition whenever the content area's size actually changes.
  const main = document.querySelector("main");
  if (main && "ResizeObserver" in window) {
    new ResizeObserver(schedulePositioning).observe(main);
  }
  main
    ?.querySelectorAll("iframe, img")
    .forEach((el) => el.addEventListener("load", schedulePositioning));
});
