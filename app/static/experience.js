/* Browser resilience and navigation enhancements; kept separate from domain logic. */
(() => {
  const nativeFetch = window.fetch.bind(window);
  window.fetch = async (input, init = {}) => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 90000);
    try {
      const response = await nativeFetch(input, { ...init, signal: init.signal || controller.signal });
      if (response.ok || response.status === 204) return response;
      const messages = {
        412: "This workspace was changed elsewhere. Reload the page to get the latest version before trying that change again.",
        428: "The workspace version is missing. Reload the page, then retry your change.",
        429: "The AI provider is rate-limiting requests. Wait a little, then retry or choose another available model.",
        502: "The selected AI provider returned an error. Check that provider's status, then retry or choose another model.",
        503: "Virtue Wise is busy or its local database is temporarily locked. Wait a moment, then retry.",
        504: "The selected AI provider took too long to respond. Retry or choose a different provider."
      };
      const message = messages[response.status];
      if (!message) return response;
      const body = await response.clone().json().catch(() => ({}));
      const headers = new Headers(response.headers);
      headers.set("Content-Type", "application/json");
      headers.delete("Content-Length");
      headers.delete("Content-Encoding");
      return new Response(JSON.stringify({ ...body, detail: message }), {
        status: response.status,
        statusText: response.statusText,
        headers
      });
    } catch (error) {
      if (error.name === "AbortError") {
        throw new Error("This request timed out. Your saved workspace has not been replaced; check the connection and retry.");
      }
      if (error instanceof TypeError) {
        throw new Error("Virtue Wise could not reach its local server. Check that the app is still running, then retry.");
      }
      throw error;
    } finally {
      window.clearTimeout(timeout);
    }
  };

  function addNavigation() {
    const header = document.querySelector(".topbar");
    const brand = header?.querySelector(".brand");
    if (!header || !brand || document.querySelector(".skip-link")) return;

    const skip = document.createElement("a");
    skip.className = "skip-link";
    skip.href = "#main-content";
    skip.textContent = "Skip to workspace";
    document.body.prepend(skip);

    const nav = document.createElement("nav");
    nav.className = "workspace-nav";
    nav.setAttribute("aria-label", "Workspace sections");
    [
      ["Start", "#intake-heading"],
      ["Evidence", "#statements-heading"],
      ["Hypotheses", "#hypotheses-heading"],
      ["Scenarios", "#scenarios-heading"],
      ["Your data", "#data-heading"]
    ].forEach(([label, target]) => {
      const link = document.createElement("a");
      link.href = target;
      link.textContent = label;
      nav.append(link);
    });
    header.append(nav);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", addNavigation, { once: true });
  } else {
    addNavigation();
  }
})();
