// Saves options to chrome.storage
function save_options() {
  var speava_session_record = document.getElementById('speava_session_record').value;
  var speava_session_spreadsheet_post = document.getElementById('speava_session_spreadsheet_post').value;
  var speava_session_username = document.getElementById('speava_session_username').value;
  var speava_session_log_string = document.getElementById('speava_session_log_string').value;
  var speava_session_send_raw = document.getElementById('speava_session_send_raw').checked;
  var speava_session_post = document.getElementById('speava_session_post').checked;
  var speava_session_show = document.getElementById('speava_session_show').checked;
  var speava_session_notification = document.getElementById('speava_session_notification_option').checked;
  var speava_session_unrecognized = document.getElementById('speava_session_unrecognized').checked;
  var speava_session_prompt = document.getElementById('speava_session_prompt').checked;
  var speava_session_option_string = document.getElementById('speava_session_option_string').value;
  var speava_session_window_positions = document.getElementById('speava_session_window_positions').value;
  var speava_session_id = document.getElementById('speava_session_id').value;
  var speava_session_text_color = document.getElementById('speava_session_text_color').value;
  var speava_oauth_client_id = document.getElementById('speava_oauth_client_id').value;

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
    speava_session_id: speava_session_id,
    speava_session_text_color: speava_session_text_color,
    speava_oauth_client_id: speava_oauth_client_id
  }, function() {
    // Update status to let user know options were saved.
    var status = document.getElementById('status');
    status.textContent = 'Options saved.';
    setTimeout(function() {
      status.textContent = '';
    }, 750);
  });
}

// Restores select box and checkbox state using the preferences
// stored in chrome.storage.
function restore_options() {
  // Use default value color = 'red' and likesColor = true.
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
    speava_session_id: "SessionName",
    speava_session_text_color: "#FFFFFF",
    speava_oauth_client_id: "987959282782-fsc8ioe25jlesviui02mm8hfa0qiga58.apps.googleusercontent.com"
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
    document.getElementById('speava_session_text_color').value = items.speava_session_text_color;
    document.getElementById('speava_oauth_client_id').value = items.speava_oauth_client_id;
  });
}
document.addEventListener('DOMContentLoaded', restore_options);
document.getElementById('speava_option_save').addEventListener('click',
    save_options);