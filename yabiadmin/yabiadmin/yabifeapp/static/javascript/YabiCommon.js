YabiGlobalEventHandler = {
  failure: function(transId, response) {
    if (response.status == 401) {
      document.location.href = appURL + 'login?error=' +
          'Could+not+connect+to+yabiadmin+server:+401+Unauthorised+returned';
    }
  }
};
Y.use('*', function(Y) {
  Y.on('io:failure', YabiGlobalEventHandler.failure, Y);
});

// Utility function namespaces.
Yabi = {
  util: {}
};


/**
 * Removes all children from the given element. Normally you'd use a library
 * that does this for you, but sadly, we're not blessed with such a beast in
 * YUI 2.
 *
 * @param {DOMElement} e The element to purge children from.
 * @return {DOMElement} The element.
 */
Yabi.util.empty = function(e) {
  while (e.childNodes.length) {
    e.removeChild(e.firstChild);
  }

  return e;
};


/**
 * Returns the offset from the top-left of the viewport for the given element.
 *
 * @return {Object} An object with "left" and "top" elements, each a number
           representing the offset from the viewport origin in pixels.
 * @type {Object}
 */
Yabi.util.getElementOffset = function(el) {
  var left = el.offsetLeft;
  var top = el.offsetTop;

  for (var parent = el.offsetParent; parent; parent = parent.offsetParent) {
    left += parent.offsetLeft;
    top += parent.offsetTop;
  }

  return {
    left: left,
    top: top
  };
};


/**
 * Returns the height of the viewport in a cross browser way.
 *
 * @return {Number} The viewport height in pixels.
 */
Yabi.util.getViewportHeight = function() {
  var height;

  if (typeof window.innerHeight != 'undefined') {
    height = window.innerHeight;
  }
  else if (typeof document.documentElement != 'undefined') {
    height = document.documentElement.clientHeight;
  }

  return height;
};


/**
 * Replaces all child elements in the given element with the new element(s).
 *
 * @param {DOMElement} e The parent element.
 * {Array.<DOMElement>} childrenElements The children elements to add.
 * @return {DOMElement} The passed in elements with children replaced.
 */
Yabi.util.replace = function(e) {
  Yabi.util.empty(e);

  for (var i = 1; i < arguments.length; i++) {
    e.appendChild(arguments[i]);
  }

  return e;
};


/**
 * Updates the given element to contain only the given text.
 *
 * @param {DOMElement} e The element.
 * @param {String} text The text to set.
 * @return {DOMElement} The passed in element with the set text.
 */
Yabi.util.text = function(e, text) {
  return Yabi.util.replace(e, document.createTextNode(text));
};

Yabi.util.doesGlobMatch = function(name, glob) {
  var matcher = Yabi.util.Glob.create(glob);
  return matcher.doesMatch(name);
};

Yabi.util.Glob = {};
Yabi.util.Glob.create = function(glob) {
  var that = {};
  that.ESCAPE_REGEX = /[-[\]{}()*+?.,\\^$|#\s]/g;
  that.regex = null;

  that.getRegex = function() {
    if (that.regex === null) {
      that.regex = that.convertGlobToRegex(glob);
    }
    return that.regex;
  };

  that.doesMatch = function(name) {
    var regex = that.convertGlobToRegex(glob);
    return regex.test(name);
  };

  that.convertGlobToRegex = function(glob) {
    var regex = '';
    var c;
    var i = 0;

    while (i < glob.length) {
      c = glob.charAt(i);
      i += 1;
      if (c === '*') {
        regex += '.*';
      } else {
        regex += that.escapeCharacter(c);
      }
    }
    return new RegExp(regex);
  };

  that.escapeCharacter = function(c) {
    return c.replace(that.ESCAPE_REGEX, '\\$&');
  };

  return that;
};


Yabi.util.Status = {};
Yabi.util.Status.getStatusImage = function(status) {
  if (status === "complete") return "ok.png";
  if (status === "error") return "error.png";
  if (status === "aborted") return "aborted.png";
  return "pending.png";
};

Yabi.util.Status.getStatusDescription = function(status) {
  if (status === "complete") return "completed";
  if (status === "error") return "errored";
  return status;
};

