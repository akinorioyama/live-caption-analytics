let user_signed_in = false;
let user_access_token = null;
let user_token_valid_through = null;
function create_oauth(client_id) {
    const CLIENT_ID = client_id;
    const REDIRECT_URI = chrome.identity.getRedirectURL();
    let auth_url = `https://accounts.google.com/o/oauth2/v2/auth?`

    var auth_params = {
    client_id: CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    response_type: 'token',
    scope: "https://www.googleapis.com/auth/userinfo.email openid",

    };
    const url = new URLSearchParams(Object.entries(auth_params));
    url.toString();
    auth_url += url;

    return auth_url;
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log("background.js called");
  if (request.message.message_type === "login") {
      if (user_signed_in && (user_access_token!==null) && (user_token_valid_through >= new Date()) ) {
          console.log("already signed in");
          sendResponse({
              message: "success",
              access_token: user_access_token,
              valid_through: user_token_valid_through
          });

      } else {
          chrome.identity.launchWebAuthFlow({
              url: create_oauth(request.message.client_id),
              interactive: true,
          }, function (redirect_uri) {
              let rep_str = redirect_uri.replace("#access_token","?access_token");
              let url = new URL(rep_str);
              user_access_token = url.searchParams.get("access_token")
              const user_access_token_through = url.searchParams.get("expires_in")
              user_token_valid_through = new Date();
              user_token_valid_through.setSeconds(user_token_valid_through.getSeconds()+ parseInt(user_access_token_through));
              console.log("token:" + user_access_token);
              console.log("token:" + user_token_valid_through.toISOString());
              if (chrome.runtime.lastError) {
                  sendResponse({
                      message: "fail"
                  });
              } else {
                  if (redirect_uri.includes("error")) {
                      user_signed_in = false;
                      sendResponse({
                          message: "fail"
                      });
                  } else {
                      //we get here but this message is never sent
                      if (user_access_token===null){
                          user_signed_in = false;
                          sendResponse({
                              message: "fail"
                      });

                      } else{
                          user_signed_in = true;
                          sendResponse({
                              message: "success",
                              access_token: user_access_token,
                              valid_through: user_token_valid_through
                      });

                      }
                  }
              }
          });
      }
  } else if (request.message.message_type === "clear"){
    chrome.identity.clearAllCachedAuthTokens(
      function(callback_check){
          // do nothing
      }
    );
    user_access_token = null;
    user_signed_in = false;
  }
  return true;
});