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

/**
 * A basic radio list element: this constructs an unordered list with the
 * appropriate event handlers to ensure that only one list item is selected at
 * a time.
 *
 * No styling is performed within this object. The top-level ul element will
 * have a "radio-list" class attached, and the selected list item will have a
 * "selected" class (guaranteed to be only one element at most).
 *
 * @constructor
 * @extends {EventEmitter}
 * @param {Element} container The containing element.
 */
var RadioList = function(container) {
  this.container = container;
  this.items = [];

  this.list = document.createElement('ul');
  this.list.className = 'radio-list';
  this.container.appendChild(this.list);

  EventEmitter.call(this);
};

RadioList.prototype = new EventEmitter();


/**
 * Creates an item within the radio list.
 *
 * @param {String|Element} label Either a string or an element to use as
 *                               the label.
 * @type {RadioListItem}
 */
RadioList.prototype.createItem = function(label) {
  var self = this;
  var item = new RadioListItem(this, label);

  this.items.push(item);
  this.list.appendChild(item.element);

  Y.use('*', function(Y) {
    var node = Y.one(item.element);
    node.on('click', function() {
      if (item.selected) {
        item.deselect();
      }
      else {
        self.selectItem(item);
      }
    });
  });

  return item;
};


/**
 * Destroys the radio list and removes it from the DOM.
 */
RadioList.prototype.destroy = function() {
  try {
    this.container.removeChild(this.list);
  }
  catch (e) {}

  this.events = {};
  this.items = [];
  this.list = null;
};


/**
 * Returns the currently selected list item.
 *
 * @return {RadioListItem} The selected item.
 */
RadioList.prototype.getSelectedItem = function() {
  for (var i = 0; i < this.items.length; i++) {
    if (this.items[i].selected) {
      return this.items[i];
    }
  }
};


/**
 * Selects the given item. Note that the "change" event is only sent if the
 * item given isn't already selected.
 *
 * @param {RadioListItem} item The item to select.
 */
RadioList.prototype.selectItem = function(item) {
  // Deselect anything that's already selected.
  for (var i = 0; i < this.items.length; i++) {
    if (this.items[i].selected) {
      // No need to reselect an already selected item.
      if (this.items[i] == item) {
        return;
      }

      this.items[i].deselect();
    }
  }

  // Select the actual item.
  item.select();

  // Send the event.
  this.sendEvent('change', item);
};



/**
 * An item within a {@see RadioList} object.
 *
 * @constructor
 * @extends {EventEmitter}
 * @param {RadioList} The list to attach the item to.
 * @param {String|Element} label Either a string or Element to use as the label.
 */
var RadioListItem = function(list, label) {
  this.list = list;
  this.label = label;
  this.selected = false;

  this.element = document.createElement('li');
  if (typeof label == 'string') {
    this.element.appendChild(document.createTextNode(label));
  }
  else {
    this.element.appendChild(label);
  }

  EventEmitter.call(this);
};

RadioListItem.prototype = new EventEmitter();


/**
 * Deselects the item and sends a "deselect" event.
 */
RadioListItem.prototype.deselect = function() {
  this.element.className = this.element.className.replace(/\bselected\b/, ' ');
  this.selected = false;
  this.sendEvent('deselect');
};


/**
 * Selects the item and sends a "select" event.
 */
RadioListItem.prototype.select = function() {
  this.element.className = this.element.className.replace(/\s*$/, ' selected');
  this.selected = true;
  this.sendEvent('select');
};
