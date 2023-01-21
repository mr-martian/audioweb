let audioBuffer;
const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
function loadAudio() {
  const request = new XMLHttpRequest();
  request.open("GET", "audio", true);
  request.responseType = "arraybuffer";
  request.onload = () => {
    let buf = request.response;
    audioCtx.decodeAudioData(
      buf,
      (b) => { audioBuffer = b; audioReady(); },
      (e) => { console.error(`Audio decode error: ${e.err}`); }
    );
  };
  request.send();
}

function play(start_ms, stop_ms) {
  let src = new AudioBufferSourceNode(audioCtx, {buffer: audioBuffer});
  src.connect(audioCtx.destination);
  src.start(0, start_ms/1000, (stop_ms-start_ms)/1000);
}

let SPAN_START = -1;

$(loadAudio);
let websocket;
function audioReady() {
  let w = Math.floor(audioBuffer.duration * 100);
  $('#editpane').width(w);
  $('#spec').width(w);
  websocket = new WebSocket(WS_ADDR);
  websocket.onmessage = ({ data }) => {
    receive(JSON.parse(data));
  };
  $('#editpane').mousedown(function(e) {
    SPAN_START = getMS(e);
  });
  $('#editpane').mouseup(function(e) {
    if (SPAN_START != -1) {
      let start = SPAN_START;
      let end = getMS(e);
      SPAN_START = -1;
      create_span(start, end);
    }
  });
  $('#editpane').mouseout(function(e) {
    if (SPAN_START != -1) {
      SPAN_START = -1;
      set_selector(0, 0);
    }
  });
  $('#editpane').mousemove(function(e) {
    if (SPAN_START != -1) {
      set_selector(SPAN_START, getMS(e));
    }
  });
  $('#span-edit-new-start,#span-edit-new-end').change(function() {
    set_selector($('#span-edit-new-start').val(), $('#span-edit-new-end').val());
  });
  $('#span-edit-new-play').click(function() {
    play($('#span-edit-new-start').val(), $('#span-edit-new-end').val());
  });
  $(window).keypress(function(e) {
    if (e.which === 32 && document.activeElement.tagName !== 'INPUT') {
      let el = $('#selector');
      play(el.data('start'), el.data('end'));
      e.preventDefault();
    }
  });
  $('#span-edit-new-save').click(function() {
    let start = parseInt($('#span-edit-new-start').val());
    let end = parseInt($('#span-edit-new-end').val());
    let tier = $('#span-edit-new-tier').val();
    let text = $('#span-edit-new-text').val();
    let ann = {
      start: start,
      end: end,
      tier: tier,
      label: text
    }
    set_selector(0, 0);
    $('.span-edit').hide();
    send({type: 'add', annotation: ann});
    add_annotation(ann);
  });
}

function click_span(e) {
  console.log('click!');
  e.preventDefault();
}

function make_tier_dropdown() {
  let tids = Object.keys(TIERS);
  tids.sort();
  let ops = tids.map((t) => {
    return '<option value="'+t+'">'+TIERS[t].name+'</option>';
  }).join('');
  $('#span-edit-new-tier').html(ops);
}

function set_selector(start_ms, end_ms) {
  if (end_ms < start_ms) {
    set_selector(end_ms, start_ms);
    return;
  }
  let start_px = start_ms / 10;
  let end_px = end_ms / 10;
  let el = document.getElementById('selector');
  el.setAttribute('data-start', start_ms);
  el.setAttribute('data-end', end_ms);
  el.style.left = start_px + 'px';
  el.style.width = (end_px - start_px) + 'px';
}

function create_span(start_ms, end_ms) {
  $('.span-edit').hide();
  make_tier_dropdown();
  $('.span-edit-new').show();
  $('#span-edit-new-start').val(start_ms);
  $('#span-edit-new-end').val(end_ms);
}

function send(data) {
  websocket.send(JSON.stringify(data));
}

let MY_ID;
let USER_NAMES = {};
let ACTIVE_USERS = [];
let TIERS = {};
let ANNOTATIONS = {};

function display_users() {
  $('#users').html(ACTIVE_USERS.map((uid) => {
    if (uid == MY_ID) {
      return '';
    } else {
      return '<li>' + USER_NAMES[uid] + '</li>';
    }
  }).join(''));
}

function display_tier(tid) {
  let el = document.createElement('div');
  el.className = 'tier';
  el.setAttribute('data-tier', tid);
  let nm = document.createElement('span');
  nm.className = 'tier-label';
  el.appendChild(nm);
  TIERS[tid].tier_elem = el;
  TIERS[tid].name_elem = nm;
  document.getElementById('tiers').appendChild(el);
}

function add_annotation(ann) {
  let el = document.createElement('div');
  el.className = 'annotation';
  el.innerHTML = '<span>' + ann.label + '</span>';
  el.style.left = (ann.start / 10) + 'px';
  $(el).width(((ann.end - ann.start)/10) + 'px');
  ann.element = el;
  ANNOTATIONS[ann.tier].push(ann);
  TIERS[ann.tier].tier_elem.appendChild(el);
  el.onclick = click_span;
}

function remove_annotation(ann) {
}

function edit_annotation(oldann, newann) {
}

function receive(event) {
  switch (event.type) {
  case 'load':
    MY_ID = event.user;
    let tids = Object.keys(event.tiers);
    tids.sort();
    tids.forEach((tid) => {
      TIERS[tid] = {name: event.tiers[tid]};
      display_tier(tid);
      ANNOTATIONS[tid] = [];
    });
    event.annotations.forEach(add_annotation);
    USER_NAMES = event.user_names;
    ACTIVE_USERS = event.active_users;
    display_users();
    break;
  case 'new_user':
    if (event.user != MY_ID) {
      ACTIVE_USERS.push(event.user);
      USER_NAMES[event.user] = event.name;
      display_users();
    }
    break;
  case 'rename_user':
    if (event.user != MY_ID) {
      USER_NAMES[event.user] = event.name;
      display_users();
    }
    break;
  case 'user_left':
    const idx = ACTIVE_USERS.indexOf(event.user);
    if (idx > -1) {
      ACTIVE_USERS.splice(idx, 1);
      display_users();
    }
    break;
  case 'add_tier':
    TIERS[event.id] = {name: event.name};
    display_tier(event.id);
    break;
  case 'rename_tier':
    if (TIERS.hasOwnProperty(event.id)) {
      TIERS[event.id].name = event.name;
      TIERS[event.id].label_elem.innerText = event.name;
    }
    break;
  case 'delete_tier':
    if (TIERS.hasOwnProperty(event.id)) {
      TIERS[event.id].tier_elem.remove();
      delete TIERS[event.id];
      delete ANNOTATIONS[event.id];
    }
    break;
  case 'add':
    if (event.user != MY_ID) {
      add_annotation(event.annotation);
    }
    break;
  case 'remove':
    if (event.user != MY_ID) {
      remove_annotation(event.annotation);
    }
    break;
  case 'edit':
    if (event.user != MY_ID) {
      edit_annotation(event.old, event.new);
    }
    break;
  default:
    console.log('unknown event', event);
  }
}

function getX(e) {
  return (e.pageX - $('#spec').offset().left);
}

function getMS(e) {
  return getX(e) * 10;
}
