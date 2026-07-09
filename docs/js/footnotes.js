document.addEventListener("DOMContentLoaded", () => {
  const refs = document.querySelectorAll("main sup a[href^='#fn']");

  refs.forEach((ref) => {
    const li = document.getElementById(ref.getAttribute("href").slice(1));
    if (!li) return;

    const sup = ref.parentElement;
    sup.classList.add("footnote-ref-wrap");

    const clone = li.cloneNode(true);
    clone.querySelectorAll("a[href^='#fnref']").forEach((a) => a.remove());

    const tooltip = document.createElement("span");
    tooltip.className = "footnote-tooltip";
    tooltip.innerHTML = clone.innerHTML.trim();
    sup.appendChild(tooltip);

    let pinned = false;
    const show = () => tooltip.classList.add("visible");
    const hide = () => {
      if (!pinned) tooltip.classList.remove("visible");
    };

    ref.addEventListener("mouseenter", show);
    ref.addEventListener("mouseleave", hide);
    ref.addEventListener("focus", show);
    ref.addEventListener("blur", hide);
    ref.addEventListener("click", (e) => {
      e.preventDefault();
      pinned = !pinned;
      tooltip.classList.toggle("visible", pinned);
    });
  });

  document.addEventListener("click", (e) => {
    document.querySelectorAll(".footnote-tooltip.visible").forEach((tooltip) => {
      if (!tooltip.parentElement.contains(e.target)) {
        tooltip.classList.remove("visible");
      }
    });
  });
});
