// Shared state of the page.
export const S = {
  data: null,        // last /api/data response
  raw: "",           // its raw text, to skip re-rendering when nothing changed
  view: "server",    // server | players | player | log
  who: null,         // player shown on the player page
  logTab: "commands",
  showArmor: true,
  ready: false,      // drawn at least once
  starting: null,    // promise while the first draw is being prepared
};
