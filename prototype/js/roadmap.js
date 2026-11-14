/*
  Roadmap page, no build step.
  State is two things: the set of finished step ids and the id of the open step.
  Every click changes the state and re-renders the page from it.
*/
(function () {
  "use strict";

  var LEVELS = window.FGOS_ROADMAP.levels;
  var STORE_KEY = "fgos.progress.v1";
  // Demo seed so the map opens mid-journey. A real account starts with [].
  var DEMO_DONE = ["l1s1", "l1s2", "l1s3", "l1s4", "l2s1"];
  // Steps that have a lesson page built.
  var LESSONS = { l2s2: "lesson.html" };

  var root = document.getElementById("app");

  function loadDone() {
    try {
      var raw = window.localStorage.getItem(STORE_KEY);
      if (raw) return JSON.parse(raw);
    } catch {
      /* storage can be unavailable; fall back to the seed */
    }
    return DEMO_DONE.slice();
  }

  function saveDone(list) {
    try {
      window.localStorage.setItem(STORE_KEY, JSON.stringify(list));
    } catch {
      /* progress then lives only in memory */
    }
  }

  var flat = [];
  LEVELS.forEach(function (level, li) {
    level.steps.forEach(function (step, si) {
      flat.push({ level: level, li: li, step: step, si: si });
    });
  });

  var done = loadDone();

  function isDone(id) {
    return done.indexOf(id) !== -1;
  }

  function currentEntry() {
    for (var i = 0; i < flat.length; i++) {
      if (!isDone(flat[i].step.id)) return flat[i];
    }
    return null;
  }

  var first = currentEntry();
  // On a wide screen the drawer opens on the current step; on a phone it would cover the map.
  var selected = window.innerWidth > 1040 && first ? first.step.id : null;

  function esc(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  var ICON = {
    star: function (size, fill) {
      return (
        '<svg aria-hidden="true" width="' + size + '" height="' + size + '" viewBox="0 0 24 24" fill="' + fill +
        '" stroke="#1D1B26" stroke-width="2.2" stroke-linejoin="round"><path d="M12 2.8l2.8 5.8 6.4.9-4.6 4.5 1.1 6.3L12 17.3l-5.7 3 1.1-6.3L2.8 9.5l6.4-.9z"/></svg>'
      );
    },
    lock: function (size) {
      return (
        '<svg aria-hidden="true" width="' + size + '" height="' + size +
        '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>'
      );
    },
    arrow:
      '<svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
    close:
      '<svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18"/></svg>',
    clock:
      '<svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/></svg>',
    flag:
      '<svg aria-hidden="true" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#1D1B26" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M6 21V4"/><path d="M6 4.5h11l-2.5 4 2.5 4H6Z" fill="#FF7FA8"/></svg>',
    logo:
      '<svg aria-hidden="true" width="32" height="32" viewBox="0 0 32 32" fill="none" stroke="#1D1B26" stroke-width="2.5" stroke-linejoin="round"><path d="M16 16.5 28 22.5 16 28.5 4 22.5Z" fill="#4DA3FF"/><path d="M16 10 28 16 16 22 4 16Z" fill="#FF7FA8"/><path d="M16 3.5 28 9.5 16 15.5 4 9.5Z" fill="#FFC83D"/></svg>'
  };

  // Where each step sits across the road: 0 centre, 1 or -1 one swing to the side.
  // Every level starts and ends at the centre, so the road passes straight through the signs.
  function roadShape(count, direction) {
    var shape = count === 4 ? [0, 1, 1, 0] : [0, 1, 0];
    return shape.map(function (k) {
      return k * direction;
    });
  }

  function renderTopbar(doneCount, xp) {
    return (
      '<header class="topbar">' +
      '<a class="brand" href="index.html">' + ICON.logo + "Freelance Growth OS</a>" +
      '<div class="pills">' +
      '<span class="pill">' + doneCount + " of " + flat.length + " steps</span>" +
      '<span class="pill pill--xp">' + ICON.star(16, "#fff") + xp + " XP</span>" +
      "</div></header>"
    );
  }

  function renderHero(cur, curLevel) {
    var next = cur
      ? '<div class="next-card t-' + cur.level.theme + '">' +
        '<div class="next-card__text">' +
        '<span class="cap">Next up · Level ' + (cur.li + 1) + "</span>" +
        '<span class="next-card__title">' + esc(cur.step.title) + "</span>" +
        '<span class="next-card__meta">' + esc(cur.level.title) + " · " + cur.step.minutes + " min · +" + cur.step.xp + " XP</span>" +
        "</div>" +
        '<button type="button" class="btn btn--primary" data-action="continue">Continue' + ICON.arrow + "</button>" +
        "</div>"
      : '<p class="next-card__title">All ' + flat.length + " steps complete.</p>";

    var slabs = LEVELS.map(function (level, li) {
      var started = level.steps.some(function (s) {
        return isDone(s.id);
      });
      return (
        '<div class="slab t-' + level.theme + (started ? " slab--solid" : " slab--ghost") +
        (li === curLevel ? " slab--float" : "") + '"></div>'
      );
    }).join("");

    return (
      '<section class="hero">' +
      '<div class="hero__text">' +
      '<span class="cap muted">Your roadmap · Web designer track</span>' +
      "<h1>Build a client-ready freelance presence</h1>" +
      '<p class="hero__lead">One road, six levels, ' + flat.length +
      " steps. Each step is a little harder than the last and ends with something you can use: a résumé, a profile, a published page, a practiced reply.</p>" +
      next +
      "</div>" +
      '<div class="tower" aria-hidden="true">' + slabs + "</div>" +
      "</section>"
    );
  }

  function renderStep(level, li, step, si, xs, direction, cur, reached, levelDone) {
    var stepDone = isDone(step.id);
    var isCurrent = cur && cur.step.id === step.id;
    var nextStep = level.steps[si + 1];
    var x = xs[si];
    var dx = nextStep ? xs[si + 1] - x : 0;
    var labelSide = x !== 0 ? x : -direction;
    var travelled = stepDone && nextStep && (isDone(nextStep.id) || (cur && cur.step.id === nextStep.id));
    var status = stepDone ? "completed" : isCurrent ? "current step" : "locked";

    var html = '<div class="row">';
    if (si === 0) html += '<span class="stub stub--top' + (reached ? " is-on" : "") + '" aria-hidden="true"></span>';
    if (!nextStep) html += '<span class="stub stub--bot' + (levelDone ? " is-on" : "") + '" aria-hidden="true"></span>';

    html +=
      '<button type="button" class="node node--' + (x === 0 ? "x0" : x > 0 ? "xp" : "xn") +
      (stepDone ? " is-done" : isCurrent ? " is-current" : " is-locked") +
      (selected === step.id ? " is-selected" : "") +
      '" data-action="open" data-id="' + step.id + '" aria-label="Step ' + (si + 1) + ": " + esc(step.title) +
      ", " + step.minutes + " minutes, " + status + '">';
    if (nextStep) {
      html += '<span class="seg seg--' + (dx === 0 ? "v" : dx > 0 ? "r" : "l") + (travelled ? " is-on" : "") + '" aria-hidden="true"></span>';
    }
    html +=
      '<span class="tile-wrap"><span class="tile"><span class="tile__face">' + (stepDone ? ICON.star(30, "#fff") : si + 1) + "</span></span></span>" +
      '<span class="lbl' + (labelSide > 0 ? "" : " lbl--left") + '">' +
      (isCurrent ? '<span class="here" aria-hidden="true">You are here</span>' : "") +
      '<span class="lbl__title">' + esc(step.title) + "</span>" +
      '<span class="lbl__meta">' + step.minutes + " min · +" + step.xp + " XP</span>" +
      "</span></button></div>";
    return html;
  }

  function renderMap(cur, curLevel) {
    var html = '<div class="map">';
    LEVELS.forEach(function (level, li) {
      var count = level.steps.length;
      var doneCount = level.steps.filter(function (s) {
        return isDone(s.id);
      }).length;
      var levelDone = doneCount === count;
      var locked = li > curLevel;
      var reached = li <= curLevel;
      var direction = li % 2 === 0 ? 1 : -1;
      var xs = roadShape(count, direction);
      var chip = levelDone
        ? "Done · " + count + " of " + count
        : locked
          ? ICON.lock(11) + "Locked"
          : doneCount + " of " + count + " steps";

      html +=
        '<section class="zone zone--' + (li + 1) + " t-" + level.theme + '" aria-label="Level ' + (li + 1) + ": " + esc(level.title) + '">' +
        '<div class="gate">' +
        '<span class="gate-line' + (li === 0 ? " gate-line--first" : "") + (reached ? " is-on" : "") + '" aria-hidden="true"></span>' +
        '<div class="sign ' + (li % 2 === 0 ? "sign--tl" : "sign--tr") + '">' +
        '<span class="sign__badge" aria-hidden="true">' + (li + 1) + "</span>" +
        '<div class="sign__body">' +
        '<div class="sign__head"><span class="cap">Level ' + (li + 1) + " · " + esc(level.tier) + '</span><span class="chip">' + chip + "</span></div>" +
        '<h2 class="sign__title">' + esc(level.title) + "</h2>" +
        '<p class="sign__blurb">' + esc(level.blurb) + "</p>" +
        "</div></div></div>";

      level.steps.forEach(function (step, si) {
        html += renderStep(level, li, step, si, xs, direction, cur, reached, levelDone);
      });

      if (li === LEVELS.length - 1) {
        html +=
          '<div class="fin">' +
          '<span class="fin-line' + (cur ? "" : " is-on") + '" aria-hidden="true"></span>' +
          '<span class="fin-badge" aria-hidden="true">' + ICON.flag + "</span>" +
          '<div class="fin-text"><strong>Finish</strong><span>A client-ready freelance presence</span></div>' +
          '<button type="button" class="reset" data-action="reset">Reset demo progress</button>' +
          "</div>";
      }
      html += "</section>";
    });
    return html + "</div>";
  }

  function renderDrawer(cur) {
    var entry = null;
    for (var i = 0; i < flat.length; i++) {
      if (flat[i].step.id === selected) entry = flat[i];
    }
    if (!entry) return "";

    var step = entry.step;
    var stepDone = isDone(step.id);
    var isCurrent = cur && cur.step.id === step.id;
    var status = stepDone ? "Completed" : isCurrent ? "Current step" : "Locked";

    var parts = step.parts
      .map(function (part, n) {
        return (
          '<li class="part"><span class="part__n">' + (n + 1) + "</span>" +
          '<span class="part__text"><span class="part__title">' + esc(part.title) + '</span><span class="part__kind">' + esc(part.kind) + "</span></span>" +
          '<span class="part__min">' + part.minutes + " min</span></li>"
        );
      })
      .join("");

    var actions;
    if (isCurrent) {
      var lesson = LESSONS[step.id];
      actions =
        '<div class="actions">' +
        (lesson
          ? '<a class="btn btn--primary grow" href="' + lesson + '">Start lesson</a>'
          : '<button type="button" class="btn btn--primary grow" disabled title="This lesson page is not built yet">Lesson coming soon</button>') +
        '<button type="button" class="btn" data-action="done">Mark as done</button>' +
        "</div>";
    } else if (stepDone) {
      actions =
        '<div class="actions actions--split">' +
        '<span class="status-line">' + ICON.star(20, "#FFC83D") + "Completed · +" + step.xp + " XP</span>" +
        "</div>";
    } else {
      actions =
        '<div class="actions actions--stack">' +
        '<p class="locked-note">' + ICON.lock(16) + "<span>Locked. Finish “" + esc(cur ? cur.step.title : "") + "” first.</span></p>" +
        '<button type="button" class="btn" data-action="continue">Go to current step</button>' +
        "</div>";
    }

    return (
      '<aside class="drawer t-' + entry.level.theme + '" aria-label="Step details">' +
      '<div class="drawer__head">' +
      '<span class="pill pill--sm pill--level cap">Level ' + (entry.li + 1) + " · " + esc(entry.level.title) + "</span>" +
      '<button type="button" class="icon-btn" data-action="close" aria-label="Close step details">' + ICON.close + "</button>" +
      "</div>" +
      '<div class="drawer__intro">' +
      '<span class="drawer__status">Step ' + (entry.si + 1) + " of " + entry.level.steps.length + " · " + status + "</span>" +
      '<h2 class="drawer__title">' + esc(step.title) + "</h2>" +
      '<p class="drawer__summary">' + esc(step.summary) + "</p>" +
      "</div>" +
      '<div class="pills">' +
      '<span class="pill pill--sm">' + ICON.clock + step.minutes + " min</span>" +
      '<span class="pill pill--sm pill--xp">' + ICON.star(14, "#fff") + "+" + step.xp + " XP</span>" +
      '<span class="pill pill--sm">' + esc(entry.level.tier) + "</span>" +
      "</div>" +
      '<div><h3 class="cap section-label">In this step</h3><ol>' + parts + "</ol></div>" +
      '<div class="outcome"><span class="cap">You finish with</span><p>' + esc(step.output) + "</p></div>" +
      actions +
      "</aside>"
    );
  }

  function render(focusId) {
    var cur = currentEntry();
    var curLevel = cur ? cur.li : LEVELS.length;
    var doneCount = flat.filter(function (f) {
      return isDone(f.step.id);
    }).length;
    var xp = flat.reduce(function (sum, f) {
      return sum + (isDone(f.step.id) ? f.step.xp : 0);
    }, 0);

    root.innerHTML =
      '<div class="wrap">' +
      renderTopbar(doneCount, xp) +
      renderHero(cur, curLevel) +
      '<main class="layout">' + renderMap(cur, curLevel) + renderDrawer(cur) + "</main>" +
      "</div>";

    // Re-rendering replaces the DOM, so put keyboard focus back where it was.
    if (focusId) {
      var node = root.querySelector('[data-id="' + focusId + '"]');
      if (node) node.focus({ preventScroll: true });
    }
  }

  root.addEventListener("click", function (event) {
    var target = event.target.closest("[data-action]");
    if (!target) return;
    var action = target.getAttribute("data-action");
    var cur = currentEntry();

    if (action === "open") {
      selected = target.getAttribute("data-id");
      render(selected);
    } else if (action === "close") {
      var last = selected;
      selected = null;
      render(last);
    } else if (action === "continue" && cur) {
      selected = cur.step.id;
      render(selected);
    } else if (action === "done" && cur) {
      done = done.concat(cur.step.id);
      saveDone(done);
      var next = currentEntry();
      selected = next ? next.step.id : cur.step.id;
      render(selected);
    } else if (action === "reset") {
      done = DEMO_DONE.slice();
      saveDone(done);
      var again = currentEntry();
      selected = window.innerWidth > 1040 && again ? again.step.id : null;
      render();
    }
  });

  render();
})();
