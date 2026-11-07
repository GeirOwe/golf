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
      if (kind === "scorecard") fillHoles(data.holes || []);
      else fillTees(data.tees || []);
      setStatus(data.message || "Hentet.", false, data.url);
    }).catch(function () {
      setStatus("Hentingen feilet. Skjemaet er uendret.", true);
    }).then(function () {
      scoreButton.disabled = false;
      ratingButton.disabled = false;
    });
  }

  scoreButton.addEventListener("click", function () { request("scorecard"); });
  ratingButton.addEventListener("click", function () { request("rating"); });
})();
