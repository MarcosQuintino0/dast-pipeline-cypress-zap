/**
 * HttpSender script for OWASP ZAP.
 *
 * This script is executed automatically for EVERY request
 * that ZAP makes during the active scan.
 *
 * Functionality:
 * - Intercepts requests before they are sent
 * - Looks for {{AUTO_INT}} tokens in the request body
 * - Replaces each token with a unique random number
 * - This ensures each scan request uses different values
 *
 * WHY IS THIS NECESSARY?
 * - During active scan, ZAP sends hundreds of requests
 * - If all use the same userId=1 or id=1, it can cause:
 *   - Database key conflicts
 *   - Rate limiting from abusing the same resource
 *   - False positives from cached responses
 * - Random values simulate real API usage
 *
 * Engine: Oracle Nashorn (JavaScript on Java)
 * Type: httpsender (intercepts HTTP requests)
 */

/**
 * Called by ZAP before sending each request.
 *
 * @param {HttpMessage} msg - ZAP's HTTP message object
 * @param {int} initiator - Who initiated the request (scanner, spider, etc.)
 * @param {HttpSenderScriptHelper} helper - ZAP helper
 */
function sendingRequest(msg, initiator, helper) {
    var body = msg.getRequestBody().toString();

    if (body && body.indexOf("{{AUTO_INT}}") > -1) {
        // Generate random number between 1000 and 99999
        var newBody = body.replace(
            /\{\{AUTO_INT\}\}/g,
            function () {
                return Math.floor(Math.random() * 98999) + 1000;
            }
        );

        msg.setRequestBody(newBody);

        // Update the Content-Length header
        msg.getRequestHeader().setContentLength(msg.getRequestBody().length());
    }
}

/**
 * Called by ZAP after receiving each response.
 * We don't do anything here, but the function must exist.
 *
 * @param {HttpMessage} msg - ZAP's HTTP message object
 * @param {int} initiator - Who initiated the request
 * @param {HttpSenderScriptHelper} helper - ZAP helper
 */
function responseReceived(msg, initiator, helper) {
    // Nothing to do on response
}
