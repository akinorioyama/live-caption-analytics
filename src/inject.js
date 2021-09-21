
try {

  const node_head = document.getElementsByTagName('head')[0];

  const css_file = document.createElement('style');
  // css_file.setAttribute('id', "test");
  css_file.setAttribute('type', "text/css");
  const url_css_file = chrome.runtime.getURL("css/style.css");
  css_file.setAttribute('src', url_css_file);
  node_head.appendChild(css_file);

  // https://stackoverflow.com/questions/46613243/uncaught-syntaxerror-unexpected-token-u-in-json-at-position-0
  // localStorage.clear()
try {

;(() => {
  ////////////////////////////////////////////////////////////////////////////
  // Variables
  ////////////////////////////////////////////////////////////////////////////

  // DOM node where Google Meet puts its closed captions
  let captionsContainer  = null;

  // The interval for attaching to the closed captions node. Once attached,
  // this can be cleared
  let closedCaptionsAttachInterval = null;

  // set to true when we are recording transcriptions
  let isTranscribing = false;
  let isShowing = false;

  // set to true if we turned on closed captions so we know to disable them
  // when we stop transcribing
  let weTurnedCaptionsOn = false;

  // used for tracking the current position in the transcription
  let currentTranscriptId = null;
  let currentSessionIndex = null;
  // now isolated to updateCurrentMeetingSession
  // let currentSpeakerIndex = null;

  let speava_session_id = "";

  // -------------------------------------------------------------------------
  // CACHE is an array of speakers and comments
  //
  // each entry contains:
  //   Speaker name, avatar, and comment
  //     person
  //     image
  //     text
  //
  //   Start and end timestamps of comment
  //     startedAt
  //     endedAt
  //
  //   Used to generate key when writing to local storage
  //     speakerIndex
  //
  //   Stored for tracking / debugging
  //     node
  //     count
  //     pollCount
  // -------------------------------------------------------------------------
  const CACHE = [];

  ////////////////////////////////////////////////////////////////////////////
  // Constants (excluding SVG, XPATH_SELECTOR, COLOR, and STYLE)
  ////////////////////////////////////////////////////////////////////////////

  // id of `svg` element of toggle button
  // used to apply the `on` class which alters the fill color of the path
  const ID_TOGGLE_BUTTON = '__gmla-icon';

  // List of ids for all recorded hangouts
  const KEY_TRANSCRIPT_IDS = 'hangouts';

  // Used to identify when the user is the speaker when listing the meeting participants
  const SEARCH_TEXT_SPEAKER_NAME_YOU = 'You';

  // Used to identify when a meeting has no name
  const SEARCH_TEXT_NO_MEETING_NAME = 'Meeting details';

  // Version of the format for localstorage data
  const LOCALSTORAGE_VERSION = 1;

  // These need to be defined below (after getOrSet is defined) because they
  // depend on that function. They're no longer constants, but they should
  // never be changed except when syncing settings.
  let SPEAKER_NAME_MAP;
  let DEBUG;
  let READONLY = false;
  let speava_async_response = null;
  let speava_async_response_show = null;
  let speava_async_response_notification = null;
  let speava_async_response_log = null;
  let speava_async_response_prompt = null;
  let isTextAreaCreated = null;
  let speava_server_url_to_record = "http://localhost:5000";
  // let speava_server_url_to_show = "http://localhost:5000/show";
  let speava_server_url_to_post = "http://localhost:5000";
  let speava_server_username = "test user";
  let speava_session_log_string = "Wonder,Mistake"
  let version = 1;
  // language check
  let language_setting_browser = window.navigator.language;
  let buttons = null;
  let speava_session_send_raw;
  let speava_session_post;
  let speava_session_show;
  let speava_session_notification;
  let speava_session_unrecognized;
  let speava_session_prompt;
  let speava_session_option_string;
  let speava_session_window_positions;

  const hostname_for_adhoc = document.location.hostname;

  let SpeechRecognition;
  let recognition;
  let finalTranscript = '';

  if (hostname_for_adhoc.match("meet.google") !== null){
    } else if (hostname_for_adhoc.match("zoom") !== null) {
    } else {
      // SpeechRecognition = webkitSpeechRecognition || SpeechRecognition;
      // recognition = new SpeechRecognition();
      // recognition.lang = 'en-US';
      // recognition.interimResults = true;
      // recognition.continuous = true;
      //   recognition.onresult = (event) => {
      //     const fixed_part_of_utterance = document.getElementById('fixed_part_of_utterance');
      //     const interim_part_of_utterance = document.getElementById('interim_part_of_utterance');
      //     let interimTranscript = '';
      //     for (let i = event.resultIndex; i < event.results.length; i++) {
      //       let transcript = event.results[i][0].transcript;
      //       if (event.results[i].isFinal) {
      //         finalTranscript += transcript + "<br>";
      //       } else {
      //         interimTranscript = transcript;
      //       }
      //     }
      //     fixed_part_of_utterance.innerHTML = finalTranscript;
      //     interim_part_of_utterance.innerHTML =  '<i style="color:#ddd;">' + interimTranscript + '</i>';
      //   }
    }

  // changed keys from __gmt to __gmla to avoid collision
  // hangouts -> meet_sessions
  ////////////////////////////////////////////////////////////////////////////
  // Local storage persistence
  //
  // Prefix for all keys: __gmt_v1_
  //  (__gmt_ when version is null, e.g. '_gmt_version')
  //
  // setting.speaker-format -> the formatting string used when copying
  //                            conversations to the cliboard
  //                            default: **HH:MM Name:** comment\n
  //
  // setting.speaker-name-map -> speaker names can be altered when copying
  //                              conversations. Names matching keys in this
  //                              object will be mapped to their respective
  //                              values
  //
  // hangouts = [<id>, ...]
  //
  // hangout_<id> = number of sessions
  //
  // hangout_<id>_session_<index> = number of speakers
  //
  // hangout_<id>_session_<index>_speaker_<index> = {
  //   person     the name of the speaker
  //   image      the url to the speaker's avatar
  //   text       the final transcription of the speaker's comment
  //   startedAt  when the speaker began making this comment
  //   endedAt    when the speaker finished making this comment
  // }
  ////////////////////////////////////////////////////////////////////////////

  // -------------------------------------------------------------------------
  // make a localStorage key with the version prefixed
  // -------------------------------------------------------------------------
  const makeFullKey = (key, version = LOCALSTORAGE_VERSION) => {
    let versionPostfix = version === null ? '' : `_v${version}`;
    return `__gmla${versionPostfix}_${key}`;
  };

  // -------------------------------------------------------------------------
  // make a localStorage key for hangouts following the format above
  // -------------------------------------------------------------------------
  const makeTranscriptKey = (...args) => {
     const [transcriptId, sessionIndex, speakerIndex] = args;

    const keyParts = [`hangout_${transcriptId}`];

    if (args.length >= 2) {
      keyParts.push(`session_${sessionIndex}`);

      if (args.length >= 3) {
        keyParts.push(`speaker_${speakerIndex}`);
      }
    }

    return keyParts.join('_');
  };

  // -------------------------------------------------------------------------
  // retrieve a key from localStorage parsed as JSON
  // -------------------------------------------------------------------------
  const get = (key, version) => {
    const raw = window.localStorage.getItem(makeFullKey(key, version));
    if (typeof raw === 'string' || raw instanceof String) {
      debug(key, raw);
      return JSON.parse(raw);
    } else {
      return raw;
    }
  };

  // -------------------------------------------------------------------------
  // retrieve a key in localStorage stringified as JSON
  // -------------------------------------------------------------------------
  const set = (key, value, version) => {
    window.localStorage.setItem(makeFullKey(key, version), JSON.stringify(value));
  };

  // -------------------------------------------------------------------------
  // delete a key from localStorage
  // -------------------------------------------------------------------------
  const remove = (key, version) => {
    debug(`remove ${makeFullKey(key, version)}`);

    if (!READONLY) {
      window.localStorage.removeItem(makeFullKey(key, version));
    }
  };

  // -------------------------------------------------------------------------
  // get a key from local storage and set it to the default if it doesn't
  // exist yet
  // -------------------------------------------------------------------------
  const getOrSet = (key, defaultValue, version) => {
    const value = get(key, version);

    if (value === undefined || value === null) {
      set(key, defaultValue, version);
      return defaultValue;
    } else {
      return value;
    }
  }

  // -------------------------------------------------------------------------
  // increment a key in local storage, set to to 0 if it doesn't exist
  // -------------------------------------------------------------------------
  const increment = (key, version) => {
    const current = get(key, version);

    if (current === undefined || current === null) {
      set(key, 0);
      return 0;
    } else {
      let next = current + 1;
      set(key, next);
      return next;
    }
  }

  ////////////////////////////////////////////////////////////////////////////
  // Settings
  ////////////////////////////////////////////////////////////////////////////

  // -------------------------------------------------------------------------
  // public getter
  // -------------------------------------------------------------------------
  window.__gmla_get = (key) => {
    return get(`setting.${key}`);
  };

  // -------------------------------------------------------------------------
  // public setter
  // -------------------------------------------------------------------------
  window.__gmla_set = (key, value) => {
    set(`setting.${key}`, value);
    syncSettings();
  };

  // -------------------------------------------------------------------------
  // public deleter
  // -------------------------------------------------------------------------
  window.__gmla_remove = (key) => {
    remove(`setting.${key}`);
    syncSettings();
  };

  // -------------------------------------------------------------------------
  // sync settings from localStorage
  // -------------------------------------------------------------------------
  const getAllStorageSyncData = () => {
    // Immediately return a promise and start asynchronous work
    return new Promise((resolve) => {
      // Asynchronously fetch all data from storage.sync.
      chrome.storage.sync.get({
      speava_session_record: 'enter URL',
      speava_session_spreadsheet_post: 'enter URL',
      speava_session_username: 'Default user',
      speava_session_log_string: 'Wonder,Mistakes',
      speava_session_send_raw: false,
      speava_session_post: false,
      speava_session_show: false,
      speava_session_notification: false,
      speava_session_unrecognized: false,
      speava_session_prompt: false,
      speava_session_option_string: null,
      speava_session_window_positions: null
    }, (items) => {
        // resolve(is_synced = true);
        is_synced = true
        // Pass any observed errors down the promise chain.
        if (chrome.runtime.lastError) {
          return reject(chrome.runtime.lastError);
        }
        // Pass the data retrieved from storage down the promise chain.
        speava_server_url_to_record = items.speava_session_record;
        speava_server_url_to_post = items.speava_session_spreadsheet_post;
        speava_server_username = items.speava_session_username;
        speava_session_log_string = items.speava_session_log_string;
        speava_session_send_raw =             items.speava_session_send_raw
        speava_session_post =                 items.speava_session_post
        speava_session_show =                 items.speava_session_show
        speava_session_notification =         items.speava_session_notification
        speava_session_unrecognized =         items.speava_session_unrecognized
        speava_session_prompt =               items.speava_session_prompt;
        speava_session_option_string =        items.speava_session_option_string;
        speava_session_window_positions =     items.speava_session_window_positions;
        let obj = { [SEARCH_TEXT_SPEAKER_NAME_YOU] :speava_server_username};
        SPEAKER_NAME_MAP = obj;

      });
    });
  }
  const syncSettings = () => {
  // -------------------------------------------------------------------------
  // sync settings from storage.sync
  // -------------------------------------------------------------------------
    chrome.storage.sync.get({
      speava_session_record: 'enter URL',
      speava_session_spreadsheet_post: 'enter URL',
      speava_session_username: 'Default user',
      speava_session_log_string: 'Wonder,Mistakes',
      speava_session_send_raw: false,
      speava_session_post: false,
      speava_session_show: false,
      speava_session_notification: false,
      speava_session_unrecognized: false,
      speava_session_prompt: false,
      speava_session_option_string: "",
      speava_session_window_positions: ""
    }, function(items) {
      speava_server_url_to_record = items.speava_session_record;
      speava_server_url_to_post = items.speava_session_spreadsheet_post;
      speava_server_username = items.speava_session_username;
      speava_session_log_string = items.speava_session_log_string;
      speava_session_send_raw =             items.speava_session_send_raw
      speava_session_post =                 items.speava_session_post  
      speava_session_show =                 items.speava_session_show
      speava_session_notification =         items.speava_session_notification
      speava_session_unrecognized =         items.speava_session_unrecognized
      speava_session_prompt =               items.speava_session_prompt;
      speava_session_option_string =        items.speava_session_option_string;
      speava_session_window_positions =     items.speava_session_window_positions;
      let obj = { [SEARCH_TEXT_SPEAKER_NAME_YOU] :speava_server_username};
      SPEAKER_NAME_MAP = obj;
    });
    DEBUG = getOrSet('setting.debug', false);
    READONLY = getOrSet('setting.readonly', false);
  };

  ////////////////////////////////////////////////////////////////////////////
  // DOM Utilities
  ////////////////////////////////////////////////////////////////////////////

  // -------------------------------------------------------------------------
  // execute an xpath query and return the first matching node
  // -------------------------------------------------------------------------
  const xpath = (search, root = document) => {
    return document.evaluate(search, root, null, XPathResult.FIRST_ORDERED_NODE_TYPE).singleNodeValue;
  };

  ////////////////////////////////////////////////////////////////////////////
  // General utilities
  ////////////////////////////////////////////////////////////////////////////

  // -------------------------------------------------------------------------
  // pad numbers 0-9 with 0
  // -------------------------------------------------------------------------
  const pad = (integer) => {
    if (integer < 10) {
      return `0${integer}`;
    } else {
      return integer;
    }
  };

  // -------------------------------------------------------------------------
  // //console.log only if DEBUG is false
  // -------------------------------------------------------------------------
  const debug = (...args) => {
    if (DEBUG) {
      console.log('[google-meet-live-analytics]', ...args);
    }
  };

  // -------------------------------------------------------------------------
  // await the function and return its value, logging an error if it rejects
  // -------------------------------------------------------------------------
  const tryTo = (fn, label) => async (...args) => {
    try {
      return await fn(...args);
    } catch (e) {
      console.error(`error ${label}:`, e);
    }
  };

  ////////////////////////////////////////////////////////////////////////////
  // Caption Controls
  ////////////////////////////////////////////////////////////////////////////

  // -------------------------------------------------------------------------
  // Turn Google's captions on
  // -------------------------------------------------------------------------
  const turnCaptionsOn = () => {
    const captionsButtonOn = xpath(`//button[@aria-label="Turn on captions (c)"]`, document);
    if (captionsButtonOn) {
      captionsButtonOn.click();
      weTurnedCaptionsOn = true;
    }
  }

  // -------------------------------------------------------------------------
  // Turn Google's captions off
  // -------------------------------------------------------------------------
  const turnCaptionsOff = () => {
    const captionsButtonOff = xpath(`//button[@aria-label='Turn off captions (c)']`, document);

    if (captionsButtonOff) {
      captionsButtonOff.click();
      weTurnedCaptionsOn = false;
    }
  }

  ////////////////////////////////////////////////////////////////////////////
  // Transcribing Controls
  ////////////////////////////////////////////////////////////////////////////

  // -------------------------------------------------------------------------
  // Stop transcribing
  // -------------------------------------------------------------------------
  const stopTranscribing = () => {
    clearInterval(closedCaptionsAttachInterval)
    closedCaptionsAttachInterval = null;
    captionContainerChildObserver.disconnect();
    captionContainerAttributeObserver.disconnect();

    document.querySelector(`#${ID_TOGGLE_BUTTON}`).classList.remove('on');
    if (weTurnedCaptionsOn) {
      turnCaptionsOff();
      turnCaptionsOff_adhoc();
      weTurnedCaptionsOn = false;
    }
  }

  // -------------------------------------------------------------------------
  // Start transcribing
  // -------------------------------------------------------------------------
  const startTranscribing = () => {
    if (closedCaptionsAttachInterval) {
      clearInterval(closedCaptionsAttachInterval);
    }

    // set this to null to force it to increment
    currentSessionIndex = null;

    closedCaptionsAttachInterval = setInterval(tryTo(closedCaptionsAttachLoop, 'attach to captions'), 1000);
    setCurrentTranscriptDetails();

    document.querySelector(`#${ID_TOGGLE_BUTTON}`).classList.add('on');
    turnCaptionsOn();
    turnCaptionsOn_adhoc();
  }

  // -------------------------------------------------------------------------
  // Toggle transcribing - invoked by `onclick` so the action doesn't need to
  // be updated each click
  // -------------------------------------------------------------------------
  const toggleTranscribing = () => {
    isTranscribing ? stopTranscribing() : startTranscribing()
    isTranscribing = !isTranscribing;
  }

  ////////////////////////////////////////////////////////////////////////////
  // Transcript reading, writing, and deleting
  ////////////////////////////////////////////////////////////////////////////

  // -------------------------------------------------------------------------
  // Update the localStorage entry for this transcript + session + speaker
  // -------------------------------------------------------------------------
  const setSpeaker = (cache) => {
    set(makeTranscriptKey(cache.transcriptId, cache.sessionIndex, cache.speakerIndex), {
      image: cache.image,
      person: cache.person,
      text: cache.text,
      startedAt: cache.startedAt,
      endedAt: cache.endedAt,
    });
  };

  // -------------------------------------------------------------------------
  // Delete all localStorage entries related to a specific transcript
  // -------------------------------------------------------------------------
  const deleteTranscript = (transcriptId,delta_index) => {
    let maxSessionIndex = get(makeTranscriptKey(transcriptId));
    // TODO: sometimes, superfluous session ID exists. Due to speaker changes?
    // Code below will preserve the last session
    // if (delta_index !== undefined){
    //   maxSessionIndex += delta_index;
    // }
    for (let sessionIndex = 0; sessionIndex <= maxSessionIndex; sessionIndex += 1) {
      let maxSpeakerIndex = get(makeTranscriptKey(transcriptId, sessionIndex));
        if (delta_index !== undefined){
          if (maxSpeakerIndex !== null) {
            if (maxSpeakerIndex !== 0){
              maxSpeakerIndex += delta_index;
            }
          }
        }
      for (let speakerIndex = 0; speakerIndex <= maxSpeakerIndex; speakerIndex += 1) {
        if (delta_index === -1) {
           if ( sessionIndex !== maxSessionIndex){
              remove(makeTranscriptKey(transcriptId, sessionIndex,speakerIndex));
           } else if ( speakerIndex !== maxSpeakerIndex){
              remove(makeTranscriptKey(transcriptId, sessionIndex,speakerIndex));
           } else {
             // console.log(sessionIndex,speakerIndex);
           }
        } else {
          remove(makeTranscriptKey(transcriptId, sessionIndex, speakerIndex));
        }
      }
      // preserve the lastest session when delta_index = -1
      if (delta_index === -1){
         if ( sessionIndex !== maxSessionIndex){
            remove(makeTranscriptKey(transcriptId, sessionIndex));
         } else {
           // console.log(sessionIndex);
         }
      } else {
        remove(makeTranscriptKey(transcriptId, sessionIndex));
      }
    }
    if (delta_index !== undefined){
      // preserve transcriptId because delta_index is intended to retain the transcriptId
      //   and remove all the captions except the latest one
      return;
    }
    remove(makeTranscriptKey(transcriptId));

    const transcriptIds = get(KEY_TRANSCRIPT_IDS) || [];
    const index = transcriptIds.indexOf(transcriptId);

    debug('would set transcript to', [...transcriptIds.slice(0, index), ...transcriptIds.slice(index + 1)]);
    if (!READONLY) {
      set(KEY_TRANSCRIPT_IDS, [...transcriptIds.slice(0, index), ...transcriptIds.slice(index + 1)]);
    }

    // query selector may run where screen is not in conf mode. Handle DOMException

    try {
      const transcriptNode = document.querySelector(`#${transcriptId}`);
      if (transcriptNode) {
        const parentNode = transcriptNode.parentNode;
        parentNode.removeChild(transcriptNode);

        if (parentNode.children.length === 0) {
          parentNode.parentNode.removeChild(parentNode.previousSibling);
          parentNode.parentNode.removeChild(parentNode);
        }
      } else {
        debug(`transcriptNode doesn't exist for ${transcriptId}`);
      }
    } catch (e) {
      if (e instanceof DOMError) {
        console.log("DOMError: potential removal in a screen where transcriptId is NOT present");
      }
      console.log(e);
    }
  }

  // -------------------------------------------------------------------------
  // Delete all transcript-specific localStorage entries
  // -------------------------------------------------------------------------
  const deleteTranscripts = () => {
    const transcriptIds = get(KEY_TRANSCRIPT_IDS) || [];

    for (let transcriptId of transcriptIds) {
      deleteTranscript(transcriptId);

    }
  };

  const cleanupOnstartupForAccumulatedTranscripts = () => {
    const transcriptIds = get(KEY_TRANSCRIPT_IDS) || [];
    if ( transcriptIds.length > 50 ){
      window.alert("The number of transcripts exceeded 50. Remove the transcript from the local machine.");
      for (let transcriptId of transcriptIds) {
        deleteTranscript(transcriptId);
      }
    }
  }

  ////////////////////////////////////////////////////////////////////////////
  // transcript and session identification
  ////////////////////////////////////////////////////////////////////////////

  // -------------------------------------------------------------------------
  // Find meeting name from footer
  // -------------------------------------------------------------------------
  const getMeetingName = () => {
    const name = xpath(`//*[text()='keyboard_arrow_up']/../..//div[@jscontroller!='']/text()`);

    if (name && name.data !== SEARCH_TEXT_NO_MEETING_NAME) {
      return name.data;
    }
  };

  // -------------------------------------------------------------------------
  // Identify the current transcript id based on the URL. Invoked whenever we
  // start trancribing.
  // -------------------------------------------------------------------------
  const setCurrentTranscriptDetails = () => {
    const now = new Date();
    const dateString = `${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())}`;
    const pathString = document.location.pathname.match(/\/(.+)/)[1];
    let newTranscriptId = `${pathString}-${dateString}`;
    const isTranscriptIdChanged = newTranscriptId !== currentTranscriptId;

    if (speava_session_id !== ""){
      newTranscriptId = speava_session_id;
    }
    if (isTranscriptIdChanged || currentSessionIndex === null) {
      currentTranscriptId = newTranscriptId;

      const transcriptIds = get(KEY_TRANSCRIPT_IDS) || [];

      if (!transcriptIds.includes(currentTranscriptId)) {
        transcriptIds.unshift(currentTranscriptId);
        set(KEY_TRANSCRIPT_IDS, transcriptIds);
      }

      currentSessionIndex = increment(`hangout_${currentTranscriptId}`);

      debug({ currentTranscriptId, currentSessionIndex });

      if (isTranscriptIdChanged) {
        const name = getMeetingName();
        if (name) {
          set(`${makeTranscriptKey(currentTranscriptId)}_name`, name);
        }
      }
    }
  };

  ////////////////////////////////////////////////////////////////////////////
  // Captions element processing
  ////////////////////////////////////////////////////////////////////////////

  const getCaptionDataZoom = () => {

    const caption_element = document.getElementById('live-transcription-subtitle');
    text = caption_element.innerText;

    return {
      image: "",
      person: speava_server_username,
      text,
    };
  };


  // -------------------------------------------------------------------------
  // Grab the speaker details and comment text for a caption node
  // -------------------------------------------------------------------------
  const getCaptionData = (node) => {
    const image = node.querySelector('img');
    const person = xpath('.//div/text()', node);
    const spans = Array.from(node.querySelectorAll('span')).filter((span) => span.children.length === 0);
    const text = spans.map((span) => span.textContent).join(' ');

    return {
      image: image.src,
      person: person.textContent,
      text,
    };
  };

  // -------------------------------------------------------------------------
  // process a change to a caption node
  //
  // If the nodes isn't being tracked yet, grab the full comment text, start
  // tracking the node, and start polling to record and save changes. The
  // goal is minimize the performance impact by capturing and saving the
  // comment once at the beginning, once at the end, and every 1 second
  // inbetween. This is reduces the amount of work done significantly for
  // longer comments.
  //
  // NOTE: It could be adjusted to only act on the last debounce if there was
  // not already a poll between the last change and time of the final call
  // -------------------------------------------------------------------------
  const updateCurrentTranscriptSession = (node) => {
    const index = CACHE.findIndex((el) => el.node === node);

    if (index === -1) {
      const currentSpeakerIndex = increment(makeTranscriptKey(currentTranscriptId, currentSessionIndex));
      CACHE.unshift({
        ...getCaptionData(node),
        startedAt: new Date(),
        endedAt: new Date(),
        node,
        count: 0,
        pollCount: 0,
        transcriptId: currentTranscriptId,
        sessionIndex: currentSessionIndex,
        speakerIndex: currentSpeakerIndex,
      });
      setSpeaker(CACHE[0]);
    } else {
      const cache = CACHE[index];

      if (cache.debounce) {
        clearInterval(cache.debounce);
      }

      cache.count += 1;
      cache.endedAt = new Date();

      cache.debounce = setInterval(
        tryTo(() => {
          cache.text = getCaptionData(node).text;
          // debug('count', cache.count, 'polls', cache.pollCount);
          setSpeaker(cache);
          clearInterval(cache.debounce);
          clearInterval(cache.poll);
          delete cache.poll;
        }, 'trailing caption poll'),
        1000
      );

      if (!('poll' in cache)) {
        cache.poll = setInterval(
          tryTo(() => {
            cache.pollCount += 1;
            cache.text = getCaptionData(node).text;
            // debug('count', cache.count, 'polls', cache.pollCount);
            setSpeaker(cache);
          }, 'caption polling'),
          1000
        );
      }
    }
  };

  ////////////////////////////////////////////////////////////////////////////
  // Captions element location and observation
  ////////////////////////////////////////////////////////////////////////////
  const findZoomCaptionContainer = () => {
    // captionContainerChildObserverZoom.disconnect();


    const caption_element = document.getElementById('live-transcription-subtitle');
    const candidates = [];

    if (caption_element === null){
      captionContainerAttributeObserverZoom.disconnect();
      captionsContainer = undefined;
      return;
    }

    if (captionsContainer !== undefined){

      // reset observer as it could be renewed
      captionContainerAttributeObserverZoom.disconnect();
      captionContainerAttributeObserverZoom.observe(caption_element, {
        attributes: true,
        subtree: true,
        // attributeFilter: ['innerText','innerHtml'],
        // attributeOldValue: true,
        characterData: true,
        characterDataOldValue: true
      })

      return captionsContainer;

    } else {

      console.log(caption_element.innerText);
      captionContainerAttributeObserverZoom.disconnect();
      captionContainerAttributeObserverZoom.observe(caption_element, {
        attributes: true,
        subtree: true,
        // attributeFilter: ['innerText','innerHtml'],
        // attributeOldValue: true,
        characterData: true,
        characterDataOldValue: true
      });
      // TODO: this has to be performed only when a new object becomes available?.
      // updateCurrentTranscriptSessionZoom(caption_element);

      return caption_element;
    }
  }

  const captionContainerAttributeObserverZoom = new MutationObserver(tryTo((mutations) => {
    console.log(mutations);
    for (let mutation of mutations) {
      console.log(mutation);
      if (mutation.type === 'characterData' && mutation.target.nodeName === '#text' ) {
        const text = mutation.target.textContent;
        const node = document.getElementById('live-transcription-subtitle');
        // TODO: text first part should match
        if (mutation.oldValue.split(" ") === mutation.target.textContent.split(" ").slice(0,mutation.oldValue.split(" ").length )){
          //updateCurrentTranscriptSessionZoom(caption_element);
          // newly push
          //TODO: add index?
          const cache = CACHE[index];

          cache.count += 1;
          cache.endedAt = new Date();
          cache.text = mutation.target.text;

          setSpeaker(cache);

        } else {

          const currentSpeakerIndex = increment(makeTranscriptKey(currentTranscriptId, currentSessionIndex));
          CACHE.unshift({
            ...getCaptionDataZoom(),
            startedAt: new Date(),
            endedAt: new Date(),
            node,
            count: 0,
            pollCount: 0,
            transcriptId: currentTranscriptId,
            sessionIndex: currentSessionIndex,
            speakerIndex: currentSpeakerIndex,
          });
          setSpeaker(CACHE[0]);

        }
      }
    }
  }, 'executing observer'));

  // -------------------------------------------------------------------------
  // Locate captions container in the DOM and attach an observer
  //
  // Strategy for finding the node for Google's closed captions:
  //
  // 1. find all img nodes from googleusercontent.com
  // 2. partition img nodes by class
  // 3. for each class, compute lowest common ancescestor of the first two
  //    nodes
  // 4. check that it is the lowest common ancestor for rest of class
  // 5. check that each node within the class has a sibling/nephew that is a
  //    leaf node with text
  // 6. check that node is centered or starts in the bottom left corner and
  //    ends between 40-90% to the right
  // -------------------------------------------------------------------------
  const findCaptionsContainer = () => {
    captionContainerChildObserver.disconnect();
    captionContainerAttributeObserver.disconnect();

    const nodesByClass = {};

    const nodes = Array.from(document.querySelectorAll('img')).filter((node) => {
        return node.src.match(/\.googleusercontent\.com\//);
    });

    for (let node of nodes) {
      if (!(node.clasName in nodesByClass)) {
        nodesByClass[node.className] = [];
      }

      nodesByClass[node.className].push(node);
    }

    const candidates = [];

    for (let classNodes of Object.values(nodesByClass)) {
      let matches = 0;

      for (let node of classNodes) {
        const spans = document.evaluate(`..//span`, node.parentElement, null, XPathResult.ORDERED_NODE_ITERATOR_TYPE);

        let span;

        while (span = spans.iterateNext()) {
          if (span.children.length === 0 && span.textContent.length > 3) {
            matches += 1;
            break;
          }
        }
      }

      if (matches !== classNodes.length) {
        continue;
      }

      let candidate = null;

      if (classNodes.length >= 2) {
        const nodeCopy = [...classNodes];
        let current = null;
        let noSharedCommonAncestor = false;

        do {
          for (let i in nodeCopy) {
            if (!nodeCopy[i].parent) {
              noSharedCommonAncestor = true;
              break;
            }

            nodeCopy[i] = nodeCopy[i].parent;

            if (i === 0) {
              current = nodeCopy[i];
            } else if (current && current !== nodeCopy[i]) {
              current = null;
            }
          }
        } while (current === null && noSharedCommonAncestor === false);

        candidate = current;

      } else {
        let node = classNodes[0];

        while (candidate === null && node) {
          if (node.getAttribute('jscontroller')) {
            candidate = node;
          } else {
            node = node.parentNode;
          }
        }
      }

      if (candidate) {
        const windowWidth = window.innerWidth;

        const rect = candidate.children[0].getBoundingClientRect();
        const isCentered = Math.abs(rect.x - rect.left) < 10;
        const isThreeFifthsWidth = Math.abs((rect.x + rect.left)*3/2 - rect.width) < 10;

        const isLeftAligned = rect.left < (windowWidth * .2);
        const isNotRightAligned = rect.right < (windowWidth * .9);
        const isWiderThanHalf = rect.right > (windowWidth * .5);

        // NOTE: could be more precise about location
        // NOTE: could explore factors that lead one of these situations to be
        //       true and then only accept candidates matching the expected case

        if (isCentered && isThreeFifthsWidth ||
            isLeftAligned && isNotRightAligned && isWiderThanHalf) {
          candidates.push(candidate);
        }
      }
    }

    // return candidates.length === 1 ? candidates[0] : null;

    if (candidates.length === 1) {
      captionContainerChildObserver.observe(candidates[0], {
        childList: true,
        subtree: true,
        // not used
        // characterData: true,
        // characterDataOldValue: true,
      });

      captionContainerAttributeObserver.observe(candidates[0], {
        attributes: true,
        subtree: false,
        attributeOldValue: true,
      });

      Array.from(candidates[0].children).forEach(tryTo((child) => {
        updateCurrentTranscriptSession(child);
      }, 'handling child node'));

      return candidates[0];
    }
  }

  // -------------------------------------------------------------------------
  // Define MutationObserver to observe the caption container
  //
  // NOTE: not a function
  // -------------------------------------------------------------------------
  const captionContainerChildObserver = new MutationObserver(tryTo((mutations) => {
    for (let mutation of mutations) {
      if (mutation.target === captionsContainer) {
        for (let node of mutation.addedNodes) {
          updateCurrentTranscriptSession(node);
        }

        // for (let node of mutation.removedNodes) {
        //   updateCurrentTranscriptSession(node);
        // }
      } else {
        const addedSpans = Array.from(mutation.addedNodes).filter((node) => {
          return node.nodeName === 'SPAN' && node.children && node.children.length === 0;
        });

        const removedSpans = Array.from(mutation.removedNodes).filter((node) => {
          return node.nodeName === 'SPAN' && node.children && node.children.length === 0;
        });

        if (addedSpans.length > 0 || removedSpans.length > 0) {
          let node = mutation.target;

          while (node && node.parentNode !== captionsContainer) {
            node = node.parentNode;
          }

          if (!node) {
            debug('could not find root for', mutation.target);
            continue;
          }

          updateCurrentTranscriptSession(node);
        }
      }
    }
  }, 'executing observer'));

  // -------------------------------------------------------------------------
  // Define MutationObserver to observe the caption container's style
  // attribute
  //
  // NOTE: not a function
  // -------------------------------------------------------------------------
  const captionContainerAttributeObserver = new MutationObserver(tryTo((mutations) => {
    for (let mutation of mutations) {
      if (mutation.attributeName === 'style') {
        const style = mutation.target.getAttribute('style');
        if (mutation.oldValue === 'display: none;' && style === '') {
          // set this to null to force it to increment
          currentSessionIndex = null;
        }
      }
    }
  }, 'executing observer'));

  // -------------------------------------------------------------------------
  // Attach to captions container 1x
  //
  // Continually attempt to locate and observe the closed captions element.
  // This needs to be re-run even after successfully attaching the user can
  // disable and re-enable closed captioning.
  // -------------------------------------------------------------------------
  const closedCaptionsAttachLoop = () => {
    // TODO avoid re-attaching tot he same container
    const hostname = document.location.hostname;
    if (hostname.match("meet.google") !== null){
      captionsContainer = findCaptionsContainer();
    } else if (hostname.match("zoom") !== null){
      captionsContainer = findZoomCaptionContainer();
    }

    debug('attached to closed captions');

    // In my experience, I haven't seen the captions container disappear but it could if
    // the user disables and re-enables captions again.
    if (captionsContainer) {
      clearInterval(closedCaptionsAttachInterval);
    }
  };

  ////////////////////////////////////////////////////////////////////////////
  // Button
  ////////////////////////////////////////////////////////////////////////////
  const getTranscript_raw = (transcriptId) => {
        const maxSessionIndex = get(makeTranscriptKey(transcriptId)) || 0;

        const speakers = [];

        for (let sessionIndex = 0; sessionIndex <= maxSessionIndex; sessionIndex += 1) {
            const maxSpeakerIndex = get(makeTranscriptKey(transcriptId, sessionIndex)) || 0;

            for (let speakerIndex = 0; speakerIndex <= maxSpeakerIndex; speakerIndex += 1) {
                const item = get(makeTranscriptKey(transcriptId, sessionIndex, speakerIndex));
                if ((item !== null) === true){
                  if (item && item.text && typeof(item.text) === "string"　&& item.text.match(/\S/g)) {
                      const dateStart = new Date(item.startedAt).toISOString();
                      const dateEnd = new Date(item.endedAt).toISOString();
                      const name = item.person in SPEAKER_NAME_MAP ? SPEAKER_NAME_MAP[item.person] : item.person;
                      speakers.push([dateStart, dateEnd, name, item.text]);
                  }
                }

            }
        }
        return speakers;
  };

  const processReceivedReplyPrompt = (response) => {
    response.json().then(function (json_text) {

        if (isTextAreaCreated !== null) {
            const feedback_textarea = xpath(`//div[@id="speava_textarea"]`, document);
            if (json_text.prompt_options !== ""){
              if (document.getElementById('option_prompt_dialog') === null){
                optionPrompt(json_text);
              }
            }
        }
    });
    speava_async_response_prompt = null;
};

  const optionPrompt = (json_text) => {
    return new Promise((resolve, reject) => {
      let dialog = document.createElement('dialog');
      let counter = 0;
      let inner_text = "";
      let heading = json_text.heading;
      let prompt_text = json_text.prompt_options;
      const time_length = json_text.setting.duration;
      dialog.id = "option_prompt_dialog"
      const msg_text = chrome.i18n.getMessage('alart_to_ask_to_answer_the_prompt');
      inner_text = `<form><div style="display:inline; font-size:48px;">${msg_text}<br></div>`;
      inner_text += `<div  style="display:inline; font-size:48px;">${heading}<br></div>`
      item_texts = prompt_text.split(",");
      for (let item_text of item_texts) {
        inner_text += `<div id="prompttext${counter}" style="display:inline; font-size:48px;">${item_text} </div>`
        counter += 1;
      }
      inner_text += `         
              <input type="text" hidden="true">
              <button type="submit" hidden="true">Ok</button>
          </form>
      `;
      dialog.innerHTML = inner_text;
      document.body.appendChild(dialog);
      dialog.oncancel = function(){
        dialog.remove();
      }
      dialog.showModal();
      if (prompt_text.length === 0) {
        setTimeout( function() {dialog.remove();}, 1000);
      } else {
        setTimeout( function() {
          const message_text = chrome.i18n.getMessage("prompt_no_answer");
          if_dialog_exist = document.getElementById('option_prompt_dialog');
          if (if_dialog_exist){
            toast_to_notify('<div style="font-size:24px;">' +
                message_text +
                '</div>',2500);
          }
          dialog.remove();
          }, time_length);
      }
      for (let new_counter = 0; new_counter < counter ;new_counter++) {
        document.getElementById(`prompttext${new_counter}`).addEventListener('click', e => {
          const message_text = chrome.i18n.getMessage("prompt_for_an_option",e.target.innerText);
          toast_to_notify('<div style="font-size:24px;">' +
              message_text +
              '</div>',2000);

          fire_log(e.target.innerText,"popup_answer");
          document.getElementById('option_prompt_dialog').remove();
        });
      }
    });
  }

    const processReceivedReplyShow = (response) => {
        response.json().then(function (json_text) {
            //console.log(json_text);
            //deleteTranscript(currentTranscriptId,-1);
            // TODO: should it be deleted in show?
            if (isTextAreaCreated !== null) {
                const feedback_textarea = xpath(`//div[@id="speava_textarea"]`, document);
                let text_for_stat = "";
                text_for_stat += json_text.heading;
                for (let item in json_text.notification) {
                    text_for_stat += json_text.notification[item] + "\t";
                }
                feedback_textarea.innerHTML = text_for_stat;
                time_length = json_text.setting.duration;
                // feedback_textarea.classList.remove("option_notification");
                setTimeout(function() {
                    speava_async_response_show = null;
                },time_length);
            }
        });
        // speava_async_response_show = null;
    };


    const processReceivedReply = (response) => {

        response.json().then(function (json_text) {
        });
        speava_async_response = null;
    };

    const processReceivedReplyLog = (response) => {
      response.json().then(function (json_text) {
      });
      speava_async_response_log = null;
    }

    const processReceivedReplyNotification = (response) => {

        response.json().then(function (json_text) {
            debug(json_text);
            let text_for_notification = "";
            for (let item in json_text.notification) {
                text_for_notification += json_text.notification[item] + "\t";
            }

            // Avoid dialog for the purpose because notification in dialog will take over the focus to the dialog popup.
            let dialog = document.getElementById("speava_session_notification");
            dialog.innerHTML = text_for_notification;
            dialog.classList.add('display_dialog');
            time_length = json_text.setting.duration;
            setTimeout(function() {
                dialog.classList.remove('display_dialog');
                speava_async_response_notification = null;
              },time_length);
        });
        // speava_async_response_notification = null;
    };

    const toast_to_notify = (input_text, duration) => {
      let dialog = document.createElement('dialog');
      dialog.innerHTML = input_text;
      document.body.appendChild(dialog);
      dialog.oncancel = function(){
        dialog.remove();
      }
      dialog.showModal();
      setTimeout( function() {dialog.remove();}, duration);
    }

    const recordingPrompt = () => {
        return new Promise((resolve, reject) => {
            let dialog = document.createElement('dialog');
            let prompt_text = getTranscript_raw(currentTranscriptId);
            let counter = 0;
            let inner_text = "";
            if (prompt_text.length === 0){
              const msg_text = chrome.i18n.getMessage('alart_to_notify_no_pending_transcript');
              inner_text = `<form><div style="display:inline; font-size:48px;">${msg_text}</div>`;
            } else {
              const msg_text = chrome.i18n.getMessage('alart_to_notify_pending_transcript');
              inner_text = `<form><div style="display:inline; font-size:48px;">${msg_text}</div>`;
            }
            for (let item of prompt_text){
              item_texts = item[3];
              item_texts = item_texts.split(" ");

//Refused to execute inline event handler because it violates the following Content Security Policy directive: "script-src 'report-sample' 'nonce-DvTNvJCQUXtCNKp34HAlHA' 'unsafe-inline' 'unsafe-eval'". Note that 'unsafe-inline' is ignored if either a hash or nonce value is present in the source list.
//               dialog.innerHTML += `<input type="text" id="hinttext${counter}" onclick="clicked_text(this){
//                               dialog.querySelector('input').value = this.innerText;
//                                   }" value="${item_text}">`
//     const clicked_text = (e) => {
//               chosen_text = e.innerText;
//               return chosen_text;
//     }
              for (let item_text of item_texts) {
                inner_text += `<div id="hinttext${counter}" style="display:inline; font-size:48px;" data-starttime="${item[0]}">${item_text} </div>`
                counter += 1;
              }
            }
            inner_text += `         
                    <input type="text" hidden="true">
                    <button type="submit" hidden="true">Ok</button>
                </form>
            `;
            dialog.innerHTML = inner_text;
            document.body.appendChild(dialog);
            dialog.oncancel = function(){
              dialog.remove();
            }
            dialog.showModal();
            if (prompt_text.length === 0) {
              setTimeout( function() {dialog.remove();}, 1000);
            }
            for (let new_counter = 0; new_counter < counter ;new_counter++) {
              document.getElementById(`hinttext${new_counter}`).addEventListener('click', e => {
                // TODO: startAt may suit better for the logging purpose as it captures the begining of the caption line
                const message_text = chrome.i18n.getMessage("record_to_review",e.target.innerText);
                toast_to_notify('<div style="font-size:24px;">' +
                    message_text +
                    '</div>',1500);

                fire_log(e.target.innerText,"unknown_word_to_review",e.target.dataset.starttime);
                document.querySelector('dialog').remove();
              });
            }
        });
    }

  const log_action = async () => {
    let input_text = await recordingPrompt();
    console.log(input_text);
    // fire a URL call to record the highlight ->alternatively fired in recordingPrompt through click eventHandler
                                 } ;

  const fire_log = (input_text,logtype, logtime=null) => {
    try {
      const now = new Date();
      const dateString = now.toISOString();
      let obj = {
        text: input_text,
        logtype: logtype,
        logtime: logtime,
        date: dateString,
        transcriptId: currentTranscriptId,
        username: speava_server_username,
        option_settings: speava_session_option_string
      }
      speava_async_response_log = fetch(speava_server_url_to_record + "/log",
          {
            method: "POST",
            mode: "cors",
            body: JSON.stringify(obj)
          });
      speava_async_response_log.then(processReceivedReplyLog).catch(error => {
        //console.log("int catch",error);
        speava_async_response_log = null;
      });
    } catch (e) {
      //console.log('catch', e);
    }
  }


  const open_option_dialog = () => {
    if (chrome.runtime.openOptionsPage) {
      chrome.runtime.openOptionsPage();
    } else {
      let dialog = document.createElement('dialog');
      let request = new Request(chrome.runtime.getURL('options.html'));
      fetch(request).then( function(response){
        return response.text().then( function(text) {
          dialog.innerHTML = text;

          dialog.oncancel = function(){
            dialog.remove();
          }

          // Saves options to chrome.storage
          const save_options = () => {
            var speava_session_record = document.getElementById('speava_session_record').value;
            var speava_session_spreadsheet_post = document.getElementById('speava_session_spreadsheet_post').value;
            var speava_session_username = document.getElementById('speava_session_username').value;
            speava_session_log_string = document.getElementById('speava_session_log_string').value;
            speava_session_send_raw = document.getElementById('speava_session_send_raw').checked;
            speava_session_post = document.getElementById('speava_session_post').checked;
            speava_session_show = document.getElementById('speava_session_show').checked;
            speava_session_notification = document.getElementById('speava_session_notification_option').checked;
            speava_session_unrecognized = document.getElementById('speava_session_unrecognized').checked;
            speava_session_prompt = document.getElementById('speava_session_prompt').checked;
            speava_session_option_string = document.getElementById('speava_session_option_string').value;
            speava_session_window_positions = document.getElementById('speava_session_window_positions').value;
            speava_session_id = document.getElementById('speava_session_id').value;
            currentTranscriptId = speava_session_id;
            speava_server_url_to_record = speava_session_record;
            speava_server_url_to_post = speava_session_spreadsheet_post;
            speava_server_username = speava_session_username;
            let obj = { [SEARCH_TEXT_SPEAKER_NAME_YOU] :speava_server_username};
            SPEAKER_NAME_MAP = obj;
            chrome.storage.sync.set({
              speava_session_record: speava_session_record,
              speava_session_spreadsheet_post: speava_session_spreadsheet_post,
              speava_session_username:speava_session_username,
              speava_session_log_string : speava_session_log_string,
              speava_session_send_raw : speava_session_send_raw,
              speava_session_post : speava_session_post,
              speava_session_show : speava_session_show,
              speava_session_notification : speava_session_notification,
              speava_session_unrecognized : speava_session_unrecognized,
              speava_session_prompt : speava_session_prompt,
              speava_session_option_string: speava_session_option_string,
              speava_session_window_positions: speava_session_window_positions,
              speava_session_id: speava_session_id
            }, function() {
              // Update status to let user know options were saved.
              let optional_buttons = document.getElementById('optional_buttons');
              while (optional_buttons.firstChild){
                optional_buttons.removeChild(optional_buttons.firstChild);
              }
              add_option_buttons(optional_buttons);
              var status = document.getElementById('status');
              status.textContent = 'Options saved.';
              setTimeout(function() {
                status.textContent = '';
                dialog.remove();
              }, 750);
            });
          }

          const restore_options = () => {
            chrome.storage.sync.get({
              speava_session_record: 'enter URL',
              speava_session_spreadsheet_post: 'enter URL',
              speava_session_username: 'Default user',
              speava_session_log_string: 'Wonder,Mistakes',
              speava_session_send_raw: false,
              speava_session_post: false,
              speava_session_show: false,
              speava_session_notification: false,
              speava_session_unrecognized: false,
              speava_session_prompt: false,
              speava_session_option_string: "",
              speava_session_window_positions: "",
              speava_session_id: ""
            }, function(items) {
              document.getElementById('speava_session_record').value = items.speava_session_record;
              document.getElementById('speava_session_spreadsheet_post').value = items.speava_session_spreadsheet_post;
              document.getElementById('speava_session_username').value = items.speava_session_username;
              document.getElementById('speava_session_log_string').value = items.speava_session_log_string;
              document.getElementById('speava_session_send_raw').checked = items.speava_session_send_raw;
              document.getElementById('speava_session_post').checked = items.speava_session_post;
              document.getElementById('speava_session_show').checked = items.speava_session_show;
              document.getElementById('speava_session_notification_option').checked = items.speava_session_notification;
              document.getElementById('speava_session_unrecognized').checked = items.speava_session_unrecognized;
              document.getElementById('speava_session_prompt').checked = items.speava_session_prompt;
              document.getElementById('speava_session_option_string').value = items.speava_session_option_string;
              document.getElementById('speava_session_window_positions').value = items.speava_session_window_positions;
              document.getElementById('speava_session_id').value = items.speava_session_id;
            });
          }
          document.body.appendChild(dialog);
          dialog.showModal();
          restore_options();
          document.getElementById('save').addEventListener('click',
            save_options);

            });
          });
    }
  }

  const fire_notification = () => {
    if (isTextAreaCreated === null ){
      return;
    }
    if (speava_session_notification === null || speava_session_notification === false){
      return;
    }
    if (speava_async_response_notification === null || speava_async_response_notification === undefined) {

      if (isShowing !== true){
        return;
      }
      if (!speava_session_notification) {
        return;
      }

      try {
        let obj = {
          transcriptId: currentTranscriptId,
          username: speava_server_username,
          option_settings: speava_session_option_string
        }
        url = speava_server_url_to_record + "/notification"
        speava_async_response_notification = fetch(url,
            {
              method: "POST",
              mode: "cors",
              body: JSON.stringify(obj)
            });
        speava_async_response_notification.then(processReceivedReplyNotification).catch(error => {
          speava_async_response_notification = null;
        });
      } catch (e) {
        //console.log('catch', e);
        speava_async_response_notification = null;
      }

    }
  }

  // -------------------------------------------------------------------------
  // Send data according to screens and settings
  //
  // -------------------------------------------------------------------------
  const sendData = () => {
    if (isTextAreaCreated !== null) {
      // caption reaction

      const element_caption_reaction = document.getElementById("speava_caption_reaction");

      if (!speava_session_unrecognized) {
        const msg_text = chrome.i18n.getMessage('realtime_caption_notify_the_option');
        element_caption_reaction.innerHTML = msg_text;

      } else {

        let prompt_text = getTranscript_raw(currentTranscriptId);
        let counter = 0;
        let inner_text = "";
        if (prompt_text.length === 0) {
          const msg_text = chrome.i18n.getMessage('realtime_no_caption_to_send_to_log');
          inner_text = `<form><div style="display:inline; font-size:48px;">${msg_text}</div>`;
        } else {
          const msg_text = chrome.i18n.getMessage('realtime_caption_to_send_to_log');
          inner_text = `<form><div style="display:inline; font-size:48px;">${msg_text}</div>`;
        }
        for (let item of prompt_text) {
          item_texts = item[3];
          item_texts = item_texts.split(" ");
          for (let item_text of item_texts) {
            inner_text += `<div id="hinttext_caption_reaction${counter}" style="display:inline; font-size:16px;" data-starttime="${item[0]}">${item_text} </div>`
            counter += 1;
          }
        }
        inner_text += `         
              <input type="text" hidden="true">
              <button type="submit" hidden="true">Ok</button>
          </form>
      `;
        element_caption_reaction.innerHTML = inner_text;

        for (let new_counter = 0; new_counter < counter; new_counter++) {
          document.getElementById(`hinttext_caption_reaction${new_counter}`).addEventListener('click', e => {
            // TODO: startAt may suit better for the logging purpose as it captures the begining of the caption line
            const message_text = chrome.i18n.getMessage("record_unrecognized", e.target.innerText);
            toast_to_notify('<div style="font-size:24px;">' +
                message_text +
                '</div>', 1500);
            fire_log(e.target.innerText,  "mistakenlyRecognized",e.target.dataset.starttime);

          });
        }
      }

      // send notification prompt request
      if (speava_session_prompt) {
        if (speava_async_response_prompt === null || speava_async_response_prompt === undefined) {
          if (isShowing === true) {
            try {
              let obj = {
                transcriptId: currentTranscriptId,
                username: speava_server_username,
                option_settings: speava_session_option_string
              }
              speava_async_response_prompt = fetch(speava_server_url_to_record + "/prompt_check",
                  {
                    method: "POST",
                    mode: "cors",
                    body: JSON.stringify(obj),
                    cache: "no-cache"
                  });
              speava_async_response_prompt.then(processReceivedReplyPrompt).catch(error => {
                //console.log("int catch",error);
                speava_async_response_prompt = null;
              });
            } catch (e) {
              //console.log('catch', e);
            }

          }
        }
      }

      if (!speava_session_notification) {
        let notification_area = document.getElementById("speava_session_notification");
        notification_area.innerHTML = chrome.i18n.getMessage("show_option_feedback");
      }
      if (!speava_session_show){
        const feedback_textarea = document.getElementById("speava_textarea");
        feedback_textarea.innerHTML = chrome.i18n.getMessage("show_stats_option");
      } else {
        if (speava_async_response_show === null || speava_async_response_show === undefined) {
          if (isShowing === true) {
            try {
              let obj = {
                transcriptId: currentTranscriptId,
                username: speava_server_username,
                option_settings: speava_session_option_string
              }
              speava_async_response_show = fetch(speava_server_url_to_record + "/show",
                  {
                    method: "POST",
                    mode: "cors",
                    body: JSON.stringify(obj),
                    cache: "no-cache"
                  });
              speava_async_response_show.then(processReceivedReplyShow).catch(error => {
                //console.log("int catch",error);
                speava_async_response_show = null;
              });
            } catch (e) {
              //console.log('catch', e);
            }

          }
        } else if (speava_async_response_show.status === undefined) {
          //console.log(speava_async_response_show);
          //console.log("undefined");
        }
      }

    }

    if (isTranscribing) {
      const transcript_text = getTranscript_raw(currentTranscriptId);
      deleteTranscript(currentTranscriptId, -1);

      if (speava_session_send_raw) {
        if (speava_async_response === null || speava_async_response === undefined) {
          try {
            let obj = {
              transcript: transcript_text,
              transcriptId: currentTranscriptId,
              username: speava_server_username,
              option_settings: speava_session_option_string
            }
            speava_async_response = fetch(speava_server_url_to_record,
                {
                  method: "POST",
                  mode: "cors",
                  body: JSON.stringify(obj)
                });
            speava_async_response.then(processReceivedReply).catch(error => {
              //console.log("int catch",error);
              speava_async_response = null;
            });
          } catch (e) {
            //console.log('catch', e);
          }
        } else if (speava_async_response.status === undefined) {
          //console.log(speava_async_response);
          //console.log("undefined");
        }
      }

      if (speava_session_post) {
        //always send to Spreadsheet. No response processing because doPost will not return the result.
        //TODO: ideally, this is decoupled from trasncribing, and activated when cc is on.

        let obj_last_only = {
          transcript: [transcript_text[transcript_text.length - 1]],
          transcriptId: currentTranscriptId,
          username: speava_server_username,
          option_settings: speava_session_option_string
        }


        fetch(speava_server_url_to_post,
            {
              method: "POST",
              mode: "cors",
              body: JSON.stringify(obj_last_only)
            });
      }
    }

  }

  // -------------------------------------------------------------------------
  // Add buttons
  //
  // Always show buttons so that users can change configuration
  //   and clear transcripts that, otherwise, sometimes prevent users from
  //   removing past captions due to unrecognized text pane
  // -------------------------------------------------------------------------
  const addButtons = () => {
    if (is_synced === null){
      return;
    }
    if (isTextAreaCreated === null) {
      const elem = document.createElement('div');
      elem.id = "speava_textarea";
      elem.style.top = "0px"
      const text = document.createTextNode('Show stats');
      const objBody = document.getElementsByTagName("body").item(0);

      //{"buttons.style.top": "160px", "elem_others.style.top": "600px","elem_others.style.right": "200px"}
      //
      let parsed_json = null;
      let buttons_style_top = '0px';
      let buttons_style_right = '100px';
      let elem_others_style_top = '0px';
      let elem_others_style_right = null;

      try {
        parsed_json = JSON.parse(speava_session_window_positions);
        if ('buttons.style.top' in parsed_json){
          buttons_style_top = parsed_json["buttons.style.top"];
        }
        if ('buttons.style.right' in parsed_json){
          buttons_style_right = parsed_json["buttons.style.right"];
        }
        if ('elem_others.style.top' in parsed_json){
          elem_others_style_top = parsed_json["elem_others.style.top"];
        }
        if ('elem_others.style.right' in parsed_json){
          elem_others_style_right = parsed_json["elem_others.style.right"];
        }

      } catch (e) {
        console.error(`error window_positions parse:`, e);
      }
      // element for non Google Meet or Zoom sites
      const hostname = document.location.hostname;
      if (hostname.match("meet.google") !== null){
      } else if (hostname.match("zoom") !== null) {
      } else {
        const elem_others = document.createElement('div');
        elem_others.id = "speava_all_others";
        // elem_others.style.zIndex = 65000;
        elem_others.style.top = elem_others_style_top;
        if (elem_others_style_right !== null) {
          elem_others.style.right = elem_others_style_right;
        }
        elem_others.style.position = 'absolute';

        // const text_others = document.createTextNode('Place holder for ad-hoc sites');
        elem_others.classList.add("option_notification")
        elem_others.innerText = 'Place holder for ad-hoc sites';
        objBody.appendChild(elem_others);
        // elem_others.appendChild(text_others);

        const toggle_button_div = document.createElement('div');
        const toggle_button = document.createElement('button');
        toggle_button.setAttribute('id',`webkit_speech_recognition_toggle`)
        toggle_button.innerText = "caption on/off";
        toggle_button.setAttribute('class',"speava_button");
        // toggle_button.style.borderRadius = "10px";
        // toggle_button.style.lineHeight = "2.5";
        toggle_button.onclick = () => {
          if ( toggle_button.classList.contains("speava_button_active")){
            recognition.stop();
            toggle_button.classList.remove('speava_button_active')
          } else {
            recognition.start();
            toggle_button.classList.add('speava_button_active')
          }
        }
        toggle_button_div.appendChild(toggle_button);
        elem_others.appendChild(toggle_button_div);
        // elem_others.appendChild(toggle_button);

        const elem_transcript = document.createElement('div');
        elem_transcript.id = "fixed_part_of_utterance";
        elem_transcript.style.zIndex = 65000;
        // elem_transcript.style.wordWrap =
        if (elem_others_style_right !== null) {
          elem_transcript.style.width = elem_others_style_right;
        }
        const elem_interim = document.createElement('div');
        elem_interim.id = "interim_part_of_utterance";
        elem_interim.style.zIndex = 65000;
        if (elem_others_style_right !== null) {
          elem_interim.style.width = elem_others_style_right;
        }
        elem_others.appendChild(elem_transcript);
        elem_others.appendChild(elem_interim);
        SpeechRecognition = webkitSpeechRecognition || SpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.lang = 'en-US';
        recognition.interimResults = true;
        recognition.continuous = true;
        recognition.onresult = (event) => {
          const fixed_part_of_utterance = document.getElementById('fixed_part_of_utterance');
          const interim_part_of_utterance = document.getElementById('interim_part_of_utterance');
          let interimTranscript = '';
          const node = document.getElementById('fixed_part_of_utterance');
          let index = fixed_part_of_utterance.speava_index;
          if (index === undefined){
            index = -1;
            fixed_part_of_utterance.speava_index = -1;
            fixed_part_of_utterance.latest_trascript_part = "";
          }
          for (let i = event.resultIndex; i < event.results.length; i++) {
            let transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              finalTranscript += "<br>" + transcript;
              finalTranscript = finalTranscript.split("<br>").slice(finalTranscript.split("<br>").length - 2,finalTranscript.split("<br>").length).join("<br>")
              // finalTranscript = finalTranscript.split("<br>").slice(0,2).join("<br>")
              const cache = CACHE[index];
              cache.count += 1;
              cache.endedAt = new Date();
              cache.text = transcript;
              setSpeaker(cache);
              fixed_part_of_utterance.speava_index = -1;
              fixed_part_of_utterance.latest_trascript_part = "";
            } else {
              interimTranscript = transcript;

              if (index===-1) {
                const currentSpeakerIndex = increment(makeTranscriptKey(currentTranscriptId, currentSessionIndex));
                CACHE.unshift({
                  ...{
                    image: "",
                    person: speava_server_username,
                    text: ""},
                  startedAt: new Date(),
                  endedAt: new Date(),
                  node,
                  count: 0,
                  pollCount: 0,
                  transcriptId: currentTranscriptId,
                  sessionIndex: currentSessionIndex,
                  speakerIndex: currentSpeakerIndex,
                });
                setSpeaker(CACHE[0]);
                fixed_part_of_utterance.speava_index += 1;
              } else {
                if ((fixed_part_of_utterance.latest_trascript_part ==="") || (transcript.split(" ").length >= 5)) {
                  if ((transcript.split(" ").length >= 5 ) &&
                      (transcript.split(" ").length >= fixed_part_of_utterance.latest_trascript_part.split(" ").length)){
                    fixed_part_of_utterance.latest_trascript_part = transcript ;
                    const cache = CACHE[index];
                    cache.count += 1;
                    cache.endedAt = new Date();
                    cache.text = transcript ;
                    setSpeaker(cache);
                  }
                }
              }

            }
          }
          fixed_part_of_utterance.innerHTML = finalTranscript;
          interim_part_of_utterance.innerHTML =  '<i style="color:#ddd;">' + interimTranscript + '</i>';
        }
        recognition.onend = function() {
          console.log("voice recognition terminated");
          if (isTranscribing === true){
            recognition.start();
            toggle_button.classList.add('speava_button_active');
          } else {
            toggle_button.classList.remove('speava_button_active')
          }
        };
      }

      elem.classList.add("option_notification")
      objBody.appendChild(elem);
      elem.appendChild(text);

      const elem_upper_container = document.createElement('div');
      elem_upper_container.id = "speava_caption_container";
      objBody.appendChild(elem_upper_container);

      const obj_container = document.getElementById("speava_caption_container")

      const elem_text_caption_reaction = document.createElement('div');
      elem_text_caption_reaction.id = "speava_caption_reaction";
      obj_container.appendChild(elem_text_caption_reaction);

      const elem_text_notification = document.createElement('div');
      elem_text_notification.id = "speava_session_notification";
      elem_text_notification.tabIndex = 4;
      obj_container.appendChild(elem_text_notification);

      isTextAreaCreated = true;

      const objBody_buttons = document.getElementsByTagName("body").item(0);
      buttons = document.createElement('div');
      isShowing = true;
      buttons.style.zIndex = 103;
      buttons.style.top = buttons_style_top;
      buttons.style.right = buttons_style_right;
      buttons.style.position = 'absolute';
      objBody_buttons.appendChild(buttons);

      const toggleButton = document.createElement('div');
      toggleButton.style.display = 'flex';
      toggleButton.style.position = 'relative';
      toggleButton.style.zIndex = 104;
      toggleButton.onclick = tryTo(toggleTranscribing, 'toggling grid');
      buttons.prepend(toggleButton);

      const clearTranscript = () => deleteTranscript(currentTranscriptId);

      const url_icon_config = chrome.runtime.getURL("icons/icon_config.png");
      const url_icon_delete = chrome.runtime.getURL("icons/icon_delete.png");
      const url_icon_record = chrome.runtime.getURL("icons/icon_record.png");
      const url_icon_log = chrome.runtime.getURL("icons/icon_log.png");

      const reactionFocus_log_action = () => log_action(currentTranscriptId);
      const open_options = () => open_option_dialog();
      const _PNG_CONFIG = {
        viewBoxWidth: 448,
        viewBoxHeight: 512,
        path: url_icon_config,
      };

      const _PNG_RECORD = {
        viewBoxWidth: 448,
        viewBoxHeight: 512,
        path: url_icon_record,
      };

      const _PNG_DELETE = {
        viewBoxWidth: 512,
        viewBoxHeight: 512,
        path: url_icon_delete,
      };

      const _PNG_LOG = {
        viewBoxWidth: 512,
        viewBoxHeight: 512,
        path: url_icon_log,
      };

      toggleButton.appendChild(makePng(_PNG_RECORD, 36, 36, { id: ID_TOGGLE_BUTTON }));

      const deleteButton = document.createElement('div');
      buttons.prepend(deleteButton);
      deleteButton.style.display = 'flex';
      deleteButton.style.position = 'relative';
      deleteButton.style.zIndex = 104;
      deleteButton.style.float = 'left';
      deleteButton.appendChild(makePng(_PNG_DELETE, 36, 36, { id: "clearTranscript", onclick: clearTranscript }));

      const configButton = document.createElement('div');
      buttons.prepend(configButton);
      configButton.style.display = 'flex';
      configButton.style.position = 'relative';
      configButton.style.zIndex = 104;
      configButton.style.float = 'left';
      configButton.appendChild(makePng(_PNG_CONFIG, 36, 36, { id: "config", onclick: open_options }));

      const logButton = document.createElement('div');
      buttons.prepend(logButton);
      logButton.style.display = 'flex';
      logButton.style.position = 'relative';
      logButton.style.zIndex = 104;
      logButton.style.float = 'left';
      logButton.appendChild(makePng(_PNG_LOG, 128, 128, { id: "log", onclick: reactionFocus_log_action }));

      const log_record_type_Button = document.createElement('div');
      buttons.prepend(log_record_type_Button);
      log_record_type_Button.style.display = "inline-flex";
      log_record_type_Button.style.flexDirection = "column";
      log_record_type_Button.id = "optional_buttons"

      add_option_buttons(log_record_type_Button);

      log_record_type_Button.style.display = 'flex';
      log_record_type_Button.style.position = 'relative';
      log_record_type_Button.style.zIndex = 104;
      log_record_type_Button.style.float = 'left';


    }

  };

  const add_option_buttons = (log_record_type_Button) => {
      const log_options = speava_session_log_string.split(",");
      let option_counter = 0;
      for (let item of log_options) {
        let log_record_type_obj = document.createElement('button');
        log_record_type_obj.setAttribute('id',`button_record_type_${option_counter}`)
        log_record_type_obj.innerText = item;
        log_record_type_obj.setAttribute('class',"speava_button");
        log_record_type_obj.addEventListener('click', e => {
          const clicked_button_text = e.target.innerText;
          const message_text = chrome.i18n.getMessage("record_log",e.target.innerText);
          toast_to_notify('<div style="font-size:24px;">' + message_text +
                          '</div>',1500);
          fire_log("no text",clicked_button_text);
        });
        log_record_type_Button.appendChild(log_record_type_obj);
        option_counter += 1;
      }

  }

  // -------------------------------------------------------------------------
  // Toggle adhoc button
  // -------------------------------------------------------------------------
  const turnCaptionsOn_adhoc = () => {
    const captionsButtonOn = xpath(`//button[@id="webkit_speech_recognition_toggle"]`, document);
    if (captionsButtonOn) {
      if (!captionsButtonOn.classList.contains("speava_button_active")){
        captionsButtonOn.click();
      }
      weTurnedCaptionsOn = true;
    }
  }

  const turnCaptionsOff_adhoc = () => {
    const captionsButtonOff =  xpath(`//button[@id="webkit_speech_recognition_toggle"]`, document);

    if (captionsButtonOff) {
      if (captionsButtonOff.classList.contains("speava_button_active")){
        captionsButtonOff.click();
      }
      weTurnedCaptionsOn = false;
    }
  }


  // -------------------------------------------------------------------------
  // Add transcript button to DOM if not present repeatedly and forever
  //
  // Continually attempt to add the transcript button if hasn't been added
  // yet. This needs to be re-run because people can join/leave meetings
  // without reloading the page.
  // -------------------------------------------------------------------------
  const addButtonLoop = () => {

    let cc_button_path;
    const hostname = document.location.hostname;
    if (hostname.match("meet.google") !== null){
      cc_button_path = `//button[contains(@aria-label,"captions (c)")]`;
      const pathString = document.location.search.match("[?&]"+"hl"+"(=([^&#]*)|&|#|$)");
      if ( pathString === null || pathString[2] !== "en") {
        const msg_string = chrome.i18n.getMessage("alert_to_change_lanauge");
        window.alert(msg_string);
      }
    } else if (hostname.match("zoom") !== null){
      cc_button_path = `//div[@class="join-audio-container"]`
      captionsContainer = findZoomCaptionContainer();
    } else {
      cc_button_path = `//div[@id="fixed_part_of_utterance"]`;
      captionsContainer = true; // pseudo object to control visibility of the buttons
    }

    // hide panes if the user is not in a meeting.
    const captionsButtonAvailability = xpath(cc_button_path, document);
    const notification_area = document.getElementById("speava_session_notification");
    const feedback_textarea = document.getElementById("speava_textarea");
    const element_caption_reaction = document.getElementById("speava_caption_reaction");
    if (captionsButtonAvailability){
      notification_area.classList.remove('display_none');
      feedback_textarea.classList.remove('display_none');
      element_caption_reaction.classList.remove('display_none');
    } else {
      notification_area.classList.add('display_none');
      feedback_textarea.classList.add('display_none');
      element_caption_reaction.classList.add('display_none');
    }
    if (buttons === null){

      const captionsButtons = xpath(`//button[contains(@aria-label,"captions (c)")]`, document);
      if (!captionsButtons){
        return;
      }
    }

  };

  const makePng = ({ viewBoxWidth, viewBoxHeight, path }, widthPx, heightPx, options = {}) => {
    const png = document.createElement('img');
    png.style.width = `${widthPx}px`;
    png.style.height = `${heightPx}px`;
    png.setAttribute('viewBox', `0 0 ${viewBoxWidth} ${viewBoxHeight}`);
    png.src = path;

    png.id = options.id ? options.id : '';
    if (options.className) {
      png.classList.add(options.className);
    }
    png.onclick = options.onclick ? options.onclick : null;

    return png;
  };

  ////////////////////////////////////////////////////////////////////////////
  // Main App
  ////////////////////////////////////////////////////////////////////////////

  console.log(`[google-meet-live-analytics] localStorage version`, getOrSet('version', 1, version = LOCALSTORAGE_VERSION));
  is_synced = null;

  getAllStorageSyncData();
  cleanupOnstartupForAccumulatedTranscripts();
  setCurrentTranscriptDetails();
  setInterval(tryTo(addButtons, 'adding buttons'), 500);
  setInterval(tryTo(addButtonLoop, 'adding button'), 500);
  setInterval(sendData,500);
  setInterval(tryTo(fire_notification, 'firing notification'), 500);

  ////////////////////////////////////////////////////////////////////////////
  // COLOR, STYLE, and SVG constants
  //
  // Moved to the bottom of the file because they're obtrusive
  ////////////////////////////////////////////////////////////////////////////

  // Add stylesheet to DOM
  const STYLE = document.createElement('style')
  const url_icon_circle = chrome.runtime.getURL("icons/icon_circle.png");
  STYLE.innerText = `#__gmla-icon.on { background-image: url("${url_icon_circle}");
                                      background-size: 36px;
                                      opacity: 0.5;
                                      z-index: 99;
                                      width:36px;
                                      height:36px;}  `
  document.head.append(STYLE);
})();

} catch (e) {
  console.error('init error', e);
}



} catch (e) {
  console.log('error injecting script', e);
}