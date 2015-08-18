/*
 * Yabi - a sophisticated online research environment for Grid, High Performance and Cloud computing.
 * Copyright (C) 2015  Centre for Comparative Genomics, Murdoch University.
 *  
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU Affero General Public License as
 *  published by the Free Software Foundation, either version 3 of the 
 *  License, or (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the 
 *  GNU Affero General Public License for more details.
 *
 *  You should have received a copy of the GNU Affero General Public License
 *  along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *  */

Y.use('*', function(Y) {
  Y.on('domready', function() {
    /**
     * Faux-singleton to implement simple message display.
     *
     * @constructor
     */
    YAHOO.ccgyabi.widget.YabiMessage = (function() {
      // Grab the containing element.
      var el = document.getElementById('yabi-message');

      // Construct the internal elements needed for display.
      var text = document.createElement('span');
      el.appendChild(text);

      var close = document.createElement('a');
      close.appendChild(document.createTextNode('[x]'));
      close.href = '#';
      el.appendChild(close);

      /* Helper function to turn a HTTP response code into a YabiMessage
       * error level. */
      var guessErrorLevel = function(status) {
        // IE handles 204 No Content as status code 1223. Yes, really.
        if ((status >= 200 && status <= 299) || status == 1223) {
          return 'success';
        }

        /* There's no point trying to distinguish warnings and errors: if
         * we're at this point, they're all errors. */
        return 'fail';
      };

      // Internal function to actually show a message with a given CSS class.
      var show = function(cls, message) {
        if (publicMethods.disabled) {
          return;
        }
        el.className = cls;

        while (text.childNodes.length > 0) {
          text.removeChild(text.firstChild);
        }
        text.appendChild(document.createTextNode(message));

        /* Get a YUI wrapped Element object so we can use setStyle() to
         * handle cross-browser differences in the opacity style. */
        var yuiEl = Y.one(el);

        yuiEl.setStyle('display', 'inline');
        yuiEl.setStyle('visibility', 'visible');
        yuiEl.setStyle('opacity', '1.0');

        window.setTimeout(function() { publicMethods.close(); }, 8000);
      };

      // The object containing the available methods to be returned.
      var publicMethods = {
        disabled: false,
        close: function() {
          var anim = new Y.Anim({
            node: Y.one(el),
            to: { opacity: 0 },
            easing: 'easeOut',
            duration: 0.25
          });
          anim.on('end', function() {
            el.style.display = 'none';
          });

          anim.run();
        },
        handleResponse: function(response) {
          if (response.statusText === 'abort') {
            return;
          }
          var message, level = guessErrorLevel(response.status);

          try {
            // Handle a valid JSON structure.
            var data = Y.JSON.parse(response.responseText);

            if ('message' in data) {
              message = data.message;
            }

            if ('level' in data) {
              level = data.level;
            }
          }
          catch (e) {
            /* No valid JSON returned, so we'll check the error level
             * based on the status code: if it appears to be a failure,
             * then we'll display a generic error message. */
            if (level == 'fail') {
              message = 'An error occurred within YABI. ' +
                        'No further information is available.';
            }
          }

          if (message) {
            show(level, message);
          }
        },
        fail: function(message) { show('fail', message); },
        success: function(message) { show('success', message); },
        warn: function(message) { show('warn', message); },

        enable: function(message) { this.disabled = false; },
        disable: function(message) { this.disabled = true; }
      };

      // Set up listeners.
      Y.one(close).on('click', function(e) {
        publicMethods.close();
        e.halt(true);
      });

      return publicMethods;
    })();
  });

});

