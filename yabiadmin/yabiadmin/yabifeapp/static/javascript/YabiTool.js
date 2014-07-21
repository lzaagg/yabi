

/**
 * YabiTool
 * render a single yabi tool
 */
function YabiTool(obj, collection, groupNode) {

  this.payload = obj;
  this.collection = collection;
  this.groupNode = groupNode;

  this.node = Y.Node.create("<div/>");
  this.node.setStyle("position", "relative");

  this.toolEl = document.createElement('div');
  this.toolEl.className = 'tool';
  this.toolEl.appendChild(document.createTextNode(this.payload.displayName));

  this.node.append(this.toolEl);

  var addEl = document.createElement('div');
  addEl.className = 'addLink';
  Y.one(addEl).on('click', collection.addCallback, null, this.payload.name);
  this.node.append(addEl);

  this.descriptionEl = document.createElement('div');
  this.descriptionEl.className = 'toolDescription';

  this.descriptionEl.appendChild(document.createTextNode(
      this.payload.description));

  //input filetypes
  this.inputsEl = document.createElement('div');
  this.inputsEl.className = 'toolHelp';
  this.inputsEl.appendChild(document.createTextNode('accepts: '));
  this.acceptedExtensionEl = document.createElement('span');
  this.acceptedExtensionEl.setAttribute('class', 'acceptedExtensionList');
  this.inputsEl.appendChild(this.acceptedExtensionEl);

  if (!Y.Lang.isArray(this.payload.inputExtensions)) {
    this.payload.inputExtensions = [this.payload.inputExtensions];
  }

  for (index in this.payload.inputExtensions) {
    ext = document.createTextNode(this.payload.inputExtensions[index]);
    spanEl = document.createElement('span');
    spanEl.setAttribute('class', 'acceptedExtension');
    spanEl.appendChild(ext);
    this.acceptedExtensionEl.appendChild(spanEl);


    this.acceptedExtensionEl.appendChild(document.createTextNode(' '));
  }

  //output filetypes
  this.outputsEl = document.createElement('div');
  this.outputsEl.className = 'toolHelp';
  this.outputsEl.appendChild(document.createTextNode('outputs: '));
  this.outputExtensionEl = document.createElement('span');
  this.outputExtensionEl.setAttribute('class', 'acceptedExtensionList');
  this.outputsEl.appendChild(this.outputExtensionEl);

  if (! Y.Lang.isUndefined(this.payload.outputExtensions)) {

    if (!Y.Lang.isArray(this.payload.outputExtensions)) {
      this.payload.outputExtensions = [this.payload.outputExtensions];
    }

    for (index in this.payload.outputExtensions) {
      ext = document.createTextNode(this.payload.outputExtensions[index]);
      spanEl = document.createElement('span');
      spanEl.setAttribute('class', 'acceptedExtension');
      spanEl.appendChild(ext);
      this.outputExtensionEl.appendChild(spanEl);

      this.outputExtensionEl.appendChild(document.createTextNode(' '));
    }
  }

  this.descriptionEl.appendChild(this.inputsEl);
  this.descriptionEl.appendChild(this.outputsEl);

  this.toolEl.appendChild(this.descriptionEl);

  Y.one(this.toolEl).on('click', this.descriptionCallback, null, this);
}

YabiTool.prototype.toString = function() {
  return this.payload.name;
};


/**
 * matchesFilter
 *
 * returns true/false if it matches text
 */
YabiTool.prototype.matchesFilter = function(needle) {
  var index, bindex, subneedle;
  var needles = [];
  var haystack = this.payload.displayName.toLowerCase();
  needle = needle.toLowerCase();

  if (haystack.indexOf(needle) != -1) {
    return true;
  }

  if (needle.indexOf('*.') === 0) {
    needle = needle.substring(2);

    for (index in this.payload.inputExtensions) {
      if (this.payload.inputExtensions[index] == needle) {
        return true;
      }
    }

    for (index in this.payload.outputExtensions) {
      if (this.payload.outputExtensions[index] == needle) {
        return true;
      }
    }
  }

  if (needle.indexOf('in:') === 0) {
    needle = needle.substring(3);

    needles = needle.split(',');

    for (bindex in needles) {
      subneedle = needles[bindex];

      if (subneedle === '*') {
        return true;
      }

      for (index in this.payload.inputExtensions) {
        if (this.payload.inputExtensions[index] == subneedle) {
          return true;
        }
      }
    }
  }

  return false;
};

YabiTool.prototype.toggleDescription = function() {
  if (this.descriptionEl.style.display !== 'block') {
    this.descriptionEl.style.display = 'block';
  } else {
    this.descriptionEl.style.display = 'none';
  }
};


//  CALLBACKS

YabiTool.prototype.descriptionCallback = function(e, target) {
  target.toggleDescription();
};


/**
 * A singleton object that exposes a get() method that implements asynchronous
 * loading of tool information, including client side caching.
 */
var YabiToolCache = (function() {
  var tools = {};

  return {
    get: function(name, success, failure) {
      if (name in tools) {
        success(tools[name]);
      } else {
        var url = appURL + 'ws/tool/' + escape(name);
        var callbacks = {
          success: function(transId, o) {
            tools[name] = o;
            success(o);
          },
          failure: function(transId, o) {
            failure(o);
          }
        };

        Y.io(url, {on: callbacks});
      }
    }
  };
})();
