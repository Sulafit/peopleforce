/*
  Lesson page: "Write your headline" (Level 2, step 2). No build step.
  The quick checks are deterministic on purpose; coaching feedback would come from the backend.
*/
(function () {
  "use strict";

  var STORE_KEY = "fgos.progress.v1";
  var DRAFT_KEY = "fgos.draft.headline.v1";
  var STEP_ID = "l2s2";
  var LIMIT = 220; // LinkedIn headline limit; recheck before launch.
  var DEMO_DONE = ["l1s1", "l1s2", "l1s3", "l1s4", "l2s1"];

  var field = document.getElementById("headline");
  var count = document.getElementById("count");
  var preview = document.getElementById("preview");
  var actions = document.getElementById("actions");
  var checks = document.querySelectorAll("[data-check]");
  var parts = document.querySelectorAll(".lesson-part");

  var saved = false;

  function read(key) {
    try {
      return window.localStorage.getItem(key);
    } catch {
      return null;
    }
  }

  function write(key, value) {
    try {
      window.localStorage.setItem(key, value);
    } catch {
      /* nothing to do: the draft stays on screen */
    }
  }

  var stored = read(DRAFT_KEY);
  if (stored !== null) field.value = stored;

  var RULES = {
    length: function (text) {
      return text.length > 0 && text.length <= LIMIT;
    },
    audience: function (text) {
      return /\bfor\b|\bhelp/i.test(text);
    },
    plain: function (text) {
      return text.length > 0 && !/guru|ninja|rockstar|wizard/i.test(text);
    }
  };

  var STAR =
    '<svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="#FFC83D" stroke="#1D1B26" stroke-width="2.2" stroke-linejoin="round"><path d="M12 2.8l2.8 5.8 6.4.9-4.6 4.5 1.1 6.3L12 17.3l-5.7 3 1.1-6.3L2.8 9.5l6.4-.9z"/></svg>';
  var TICK =
    '<svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#1D1B26" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5 10 17.5 19 7.5"/></svg>';

  function update() {
    var text = field.value;
    var length = text.length;
    var canSave = RULES.length(text);

    count.textContent = length + " / " + LIMIT;
    count.classList.toggle("is-over", length > LIMIT);
    preview.textContent = text || "Your headline appears here";

    checks.forEach(function (item) {
      var ok = RULES[item.getAttribute("data-check")](text);
      item.classList.toggle("is-ok", ok);
      var mark = item.querySelector(".check__mark");
      mark.innerHTML = ok ? TICK : "";
      mark.setAttribute("aria-label", ok ? "Passed" : "Not yet");
    });

    // Parts 3 and 4 complete once the headline is saved.
    parts[2].className = "lesson-part " + (saved ? "is-done" : "is-active");
    parts[3].className = "lesson-part " + (saved ? "is-done" : "");

    if (saved) {
      actions.className = "actions actions--split";
      actions.innerHTML =
        '<span class="status-line">' + STAR + "Saved to your Freelancer Profile · +40 XP</span>" +
        '<a class="btn btn--primary" href="index.html">Back to roadmap</a>';
    } else if (canSave) {
      actions.className = "actions";
      actions.innerHTML = '<button type="button" class="btn btn--primary" id="save">Save headline</button>';
    } else {
      actions.className = "actions";
      actions.innerHTML =
        '<button type="button" class="btn btn--primary" disabled>Save headline</button>' +
        '<span class="hint hint--error">Keep it between 1 and ' + LIMIT + " characters to save.</span>";
    }
  }

  field.addEventListener("input", function () {
    saved = false;
    write(DRAFT_KEY, field.value);
    update();
  });

  actions.addEventListener("click", function (event) {
    if (!event.target.closest("#save")) return;
    saved = true;
    write(DRAFT_KEY, field.value);

    // Saving the artifact completes the step on the roadmap.
    var done;
    try {
      done = JSON.parse(read(STORE_KEY)) || DEMO_DONE.slice();
    } catch {
      done = DEMO_DONE.slice();
    }
    if (done.indexOf(STEP_ID) === -1) done.push(STEP_ID);
    write(STORE_KEY, JSON.stringify(done));

    update();
    var back = actions.querySelector("a");
    if (back) back.focus();
  });

  update();
})();
