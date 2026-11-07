(function () {
  var form = document.querySelector("#course-form");
  var scoreButton = document.querySelector("#fetch-scorecard");
  var ratingButton = document.querySelector("#fetch-ratings");
  var status = document.querySelector("#fetch-status");
  if (!form || !scoreButton || !ratingButton || !status) return;

  function setStatus(text, isError, url) {
    status.textContent = "";
    status.classList.toggle("field__error", !!isError);
    status.appendChild(document.createTextNode(text));
    if (!isError && typeof url === "string" && url.indexOf("https://") === 0) {
      status.appendChild(document.createTextNode(" "));
      var link = document.createElement("a");
      link.href = url;
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = "Kilde";
      status.appendChild(link);
    }
  }

  function numberInput(name, value, min, max) {
    var input = document.createElement("input");
    input.className = "input";
    input.type = "number";
    input.name = name;
    input.min = String(min);
    input.max = String(max);
    input.step = "1";
    input.value = value === undefined || value === null ? "" : String(value);
    return input;
  }

  function holeRow(hole, maxIndex) {
    var row = document.createElement("tr");
    var numberCell = document.createElement("td");
    numberCell.appendChild(numberInput("hole_number", hole.number, 1, 54));
    var parCell = document.createElement("td");
    parCell.className = "num";
    parCell.appendChild(numberInput("hole_par", hole.par, 3, 6));
    var indexCell = document.createElement("td");
    indexCell.className = "num";
    indexCell.appendChild(numberInput("hole_stroke_index", hole.stroke_index, 1, maxIndex));
    var meterCell = document.createElement("td");
    meterCell.className = "num";
    meterCell.appendChild(numberInput("hole_meters", hole.meters, 30, 750));
    row.appendChild(numberCell);
    row.appendChild(parCell);
    row.appendChild(indexCell);
    row.appendChild(meterCell);
    return row;
  }

  function fillHoles(holes) {
    var front = document.querySelector("#hole-rows-front");
    var back = document.querySelector("#hole-rows-back");
    var frontWrap = document.querySelector("#hole-front-wrap");
    var backWrap = document.querySelector("#hole-back-wrap");
    var countInput = document.querySelector("#hole_count");
    if (!front || !back || !countInput) return;
    var maxIndex = holes.length || 18;
    front.textContent = "";
    back.textContent = "";
    holes.forEach(function (hole) {
      var row = holeRow(hole, maxIndex);
      if (Number(hole.number) <= 9) front.appendChild(row);
      else back.appendChild(row);
    });
    if (frontWrap) frontWrap.hidden = !front.children.length;
    if (backWrap) backWrap.hidden = !back.children.length;
    countInput.value = String(holes.length);
    var empty = form.querySelector(".empty");
    if (empty && holes.length) empty.hidden = true;
    updateParSums();
  }

  function field(row, name) {
    return row.querySelector('[name="' + name + '"]');
  }

  function fillTee(row, tee) {
    field(row, "tee_name").value = tee.name;
    field(row, "tee_gender").value = tee.gender;
    field(row, "tee_par").value = tee.par;
    field(row, "tee_cr").value = tee.course_rating;
    field(row, "tee_slope").value = tee.slope_rating;
    ["tee_name", "tee_par", "tee_cr", "tee_slope"].forEach(function (name) {
      field(row, name).required = true;
    });
  }

  function blankTee(row) {
    var copy = row.cloneNode(true);
    field(copy, "tee_id").value = "";
    field(copy, "tee_name").value = "";
    field(copy, "tee_name").removeAttribute("required");
    field(copy, "tee_gender").value = "Herre";
    ["tee_par", "tee_cr", "tee_slope"].forEach(function (name) {
      field(copy, name).value = "";
      field(copy, name).removeAttribute("required");
    });
    copy.querySelectorAll(".tee-example").forEach(function (cell) {
      cell.textContent = "–";
    });
    return copy;
  }

  var picker = document.querySelector("#rating-picker");
  var choices = document.querySelector("#rating-choices");
  var applyButton = document.querySelector("#rating-apply");
  var cancelButton = document.querySelector("#rating-cancel");
  var pending = null;

  function ratingLabel(tee) {
    var rating = String(tee.course_rating).replace(".", ",");
    return tee.name + " · " + tee.gender + " · par " + tee.par
      + " · CR " + rating + " · slope " + tee.slope_rating;
  }

  function hidePicker() {
    pending = null;
    if (choices) choices.textContent = "";
    if (picker) picker.hidden = true;
  }

  function showRatingPicker(data) {
    if (!picker || !choices) {
      fillTees(data.tees || []);
      return;
    }
    pending = data;
    choices.textContent = "";
    (data.tees || []).forEach(function (tee, index) {
      var label = document.createElement("label");
      label.className = "check-row";
      var input = document.createElement("input");
      input.type = "checkbox";
      input.value = String(index);
      input.checked = tee.gender === "Herre";
      label.appendChild(input);
      label.appendChild(document.createTextNode(" " + ratingLabel(tee)));
      choices.appendChild(label);
    });
    picker.hidden = false;
  }

  function fillTees(tees) {
    var body = document.querySelector("#tee-rows");
    if (!body) return;
    var rows = Array.prototype.slice.call(body.querySelectorAll(".tee-row"));
    tees.forEach(function (tee) {
      var match = rows.filter(function (row) {
        return field(row, "tee_name").value.trim() === String(tee.name)
          && field(row, "tee_gender").value === tee.gender;
      })[0];
      if (!match) {
        match = rows.filter(function (row) {
          return !field(row, "tee_name").value.trim();
        })[0];
      }
      if (!match) {
        match = blankTee(rows[rows.length - 1]);
        body.appendChild(match);
        rows.push(match);
      }
      fillTee(match, tee);
    });
    updateParSums();
  }

  function wholeNumber(value) {
    var text = String(value == null ? "" : value).trim();
    if (!/^-?\d+$/.test(text)) return null;
    return Number(text);
  }

  function teeDifferences(differing) {
    var grouped = [];
    var indexByPar = {};
    differing.forEach(function (item) {
      if (indexByPar[item.par] === undefined) {
        indexByPar[item.par] = grouped.length;
        grouped.push({par: item.par, labels: []});
      }
      grouped[indexByPar[item.par]].labels.push(item.label);
    });
    return grouped.map(function (group) {
      return group.labels.join(", ") + " har par " + group.par;
    }).join(". ") + ".";
  }

  function updateParSums() {
    var summary = document.querySelector("#par-summary");
    if (!summary) return;
    var groups = {front: [], back: [], extra: []};
    var incomplete = false;
    var seen = false;
    form.querySelectorAll("#hole-rows-front tr, #hole-rows-back tr").forEach(function (row) {
      var number = wholeNumber(field(row, "hole_number").value);
      var par = wholeNumber(field(row, "hole_par").value);
      if (number === null && par === null) return;
      seen = true;
      if (number === null || par === null) {
        incomplete = true;
        return;
      }
      if (number <= 9) groups.front.push(par);
      else if (number <= 18) groups.back.push(par);
      else groups.extra.push(par);
    });
    if (!seen || incomplete) {
      summary.hidden = true;
      summary.textContent = "";
      summary.classList.remove("field__error");
      return;
    }
    var sum = function (values) {
      return values.reduce(function (total, value) { return total + value; }, 0);
    };
    var bits = [];
    if (groups.front.length) bits.push("par 1–9 er " + sum(groups.front));
    if (groups.back.length) bits.push("par 10–18 er " + sum(groups.back));
    var total = sum(groups.front) + sum(groups.back) + sum(groups.extra);
    bits.push("totalt " + total);
    var text = bits.join(", ");
    text = text.charAt(0).toUpperCase() + text.slice(1) + ".";
    var teeItems = [];
    form.querySelectorAll("#tee-rows .tee-row").forEach(function (row) {
      var par = wholeNumber(field(row, "tee_par").value);
      if (par === null) return;
      var name = field(row, "tee_name").value.trim();
      var gender = field(row, "tee_gender").value.trim();
      var label = name && gender ? name + " " + gender : (name || "tee");
      teeItems.push({label: label, par: par});
    });
    var matches = teeItems.some(function (item) { return item.par === total; });
    var differing = teeItems.filter(function (item) { return item.par !== total; });
    summary.classList.remove("field__error");
    if (teeItems.length && matches && !differing.length) {
      text += " Stemmer med tee-par " + total + ".";
    } else if (teeItems.length && matches) {
      text += " Stemmer med tee-par " + total + ". " + teeDifferences(differing);
    } else if (teeItems.length) {
      var pars = [];
      teeItems.forEach(function (item) {
        if (pars.indexOf(item.par) === -1) pars.push(item.par);
      });
      pars.sort(function (a, b) { return a - b; });
      text += " Stemmer ikke med tee-par " + pars.join(", ") + ".";
      summary.classList.add("field__error");
    }
    summary.hidden = false;
    summary.textContent = text;
  }

  function request(kind) {
    var name = document.querySelector("#name").value.trim();
    var facility = document.querySelector("#facility").value.trim();
    scoreButton.disabled = true;
    ratingButton.disabled = true;
    setStatus(kind === "scorecard" ? "Henter scorekort …" : "Henter CR/Slope …", false);
    fetch(form.getAttribute("data-fetch-url"), {
      method: "POST",
      headers: {"Content-Type": "application/json", "Accept": "application/json"},
      body: JSON.stringify({kind: kind, name: name, facility: facility})
    }).then(function (response) {
      return response.json();
    }).then(function (data) {
      if (!data || !data.ok) {
        setStatus((data && data.error) || "Hentingen feilet. Skjemaet er uendret.", true);
        return;
      }
      if (kind === "scorecard") {
        fillHoles(data.holes || []);
        setStatus(data.message || "Hentet.", false, data.url);
      } else {
        showRatingPicker(data);
        setStatus("Velg tee-stedene som skal med.", false, data.url);
      }
    }).catch(function () {
      setStatus("Hentingen feilet. Skjemaet er uendret.", true);
    }).then(function () {
      scoreButton.disabled = false;
      ratingButton.disabled = false;
    });
  }

  form.addEventListener("input", refreshParSums);
  form.addEventListener("change", refreshParSums);
  function refreshParSums(event) {
    var name = event.target && event.target.name;
    if (name === "hole_par" || name === "hole_number" || name === "tee_par" || name === "tee_name" || name === "tee_gender") {
      updateParSums();
    }
  }
  updateParSums();

  scoreButton.addEventListener("click", function () { request("scorecard"); });
  ratingButton.addEventListener("click", function () { request("rating"); });
  if (applyButton) {
    applyButton.addEventListener("click", function () {
      if (!pending) return;
      var selected = [];
      choices.querySelectorAll("input[type=checkbox]:checked").forEach(function (input) {
        var tee = (pending.tees || [])[Number(input.value)];
        if (tee) selected.push(tee);
      });
      if (!selected.length) {
        setStatus("Velg minst ett tee-sted. Skjemaet er uendret.", true);
        return;
      }
      fillTees(selected);
      var count = selected.length === 1 ? "1 tee-sted lagt inn." : selected.length + " tee-steder lagt inn.";
      var message = pending.message ? pending.message + " " + count : count;
      var url = pending.url;
      hidePicker();
      setStatus(message, false, url);
    });
  }
  if (cancelButton) {
    cancelButton.addEventListener("click", function () {
      hidePicker();
      setStatus("Ingen tee-steder ble lagt inn. Skjemaet er uendret.", false);
    });
  }
})();
