YUI().use('node', 'event', 'io', 'json-parse', 'yui2-slider', function(Y) {

  /**
   * YabiWorkflowCollection
   * fetch and render listing/grouping/smart filtering of workflows
   */
  YabiWorkflowCollection = function() {
    this.workflows = [];

    //util fn
    var dblzeropad = function(number) {
      if (number < 10) {
        number = '0' + number;
      }
      return number;
    };

    var defaultStartDate = new Date();
    defaultStartDate.setDate(defaultStartDate.getDate() - 7);
    this.dateStart = defaultStartDate.getFullYear() + '-' +
        dblzeropad(defaultStartDate.getMonth() + 1) + '-' +
        dblzeropad(defaultStartDate.getDate());

    this.loadedWorkflow = null;
    this.loadedWorkflowEl = document.createElement('div');
    this.loadedWorkflowOptionsEl = document.createElement('div');
    this.loadedWorkflowFileOutputsEl = document.createElement('div');
    this.loadedWorkflowStatusEl = document.createElement('div');

    this.containerEl = document.createElement('div');
    this.containerEl.className = 'workflowCollection';

    this.filterEl = document.createElement('div');
    this.filterEl.className = 'filterPanel';

    this.searchLabelEl = document.createElement('label');
    this.searchLabelEl.appendChild(document.createTextNode('Find: '));
    this.filterEl.appendChild(this.searchLabelEl);

    this.searchEl = document.createElement('input');
    this.searchEl.setAttribute('type', 'search');
    this.searchEl.className = 'toolSearchField';

    //attach key events for changes/keypresses
    Y.one(this.searchEl).on('blur', this.filterCallback, null, this);
    Y.one(this.searchEl).on('keyup', this.filterCallback, null, this);
    Y.one(this.searchEl).on('change', this.filterCallback, null, this);
    Y.one(this.searchEl).on('search', this.filterCallback, null, this);

    this.filterEl.appendChild(this.searchEl);

    this.clearFilterEl = document.createElement('span');
    this.clearFilterEl.className = 'fakeButton';
    this.clearFilterEl.appendChild(document.createTextNode('show all'));
    this.clearFilterEl.style.visibility = 'hidden';
    Y.one(this.clearFilterEl).on('click', this.clearFilterCallback, null, this);

    this.filterEl.appendChild(this.clearFilterEl);

    //date slider
    this.sliderContainerEl = document.createElement('div');
    this.sliderContainerEl.className = 'sliderContainer';
    var labelDiv = document.createElement('div');
    //this.sliderContainerEl.className = 'sliderContainer yui3-skin-sam';
    //var labelDiv = document.createElement('span');
    labelDiv.className = 'sliderLabel';
    labelDiv.appendChild(document.createTextNode('Date range:'));
    this.sliderContainerEl.appendChild(labelDiv);
    //this.sliderEl = document.createElement('span');
    this.sliderEl = document.createElement('div');
    //Y.one(this.sliderEl).setStyles({'left': '150px'});
    //this.sliderContainerEl.appendChild(this.sliderEl);

    this.sliderEl.className = 'yui-h-slider slider-bg';
    this.slideThumbEl = document.createElement('div');
    this.slideThumbEl.className = 'yui-slider-thumb slider-thumb';
    this.sliderEl.appendChild(this.slideThumbEl);
    this.sliderContainerEl.appendChild(this.sliderEl);
    this.sliderValueEl = document.createElement('div');
    this.sliderValueEl.className = 'sliderValue';
    this.sliderValueEl.appendChild(document.createTextNode('past 7 days'));
    this.sliderContainerEl.appendChild(this.sliderValueEl);

    this.filterEl.appendChild(this.sliderContainerEl);

    this.slider = Y.YUI2.widget.Slider.getHorizSlider(this.sliderEl,
        this.slideThumbEl, 0, 160, 40);
    this.slider.animate = true;
    this.slider.setValue(40, true, false, true);


    //this.slider = new Y.Slider();
    //this.slider.render(this.sliderEl);
    //this.slider.syncUI();

    this.statusFilterContainer = document.createElement('div');
    this.statusFilterContainer.className = 'filterStatus';
    this.statusFilterContainer.appendChild(document.createTextNode('Status: '));

    var statuses = ['All', 'Ready', 'Complete'];
    this.statusEls = [];
    var tmpItem;
    for (var index in statuses) {
      tmpItem = document.createElement('span');
      tmpItem.className = 'statusFilter';
      tmpItem.appendChild(document.createTextNode(statuses[index]));
      this.statusFilterContainer.appendChild(tmpItem);
      Y.one(tmpItem).on('click', this.statusFilterCallback, null,
          {'target': this, 'value': statuses[index], 'el': tmpItem});

      this.statusEls[statuses[index]] = tmpItem;
    }

    //default status filter is All
    this.statusEls.All.className = 'selectedStatusFilter';
    this.statusFilterValue = 'All';

    this.filterEl.appendChild(this.statusFilterContainer);

    this.containerEl.appendChild(this.filterEl);

    //no results div
    this.noResultsDiv = document.createElement('div');
    this.noResultsDiv.className = 'wfNoResultsDiv';
    this.noResultsDiv.appendChild(document.createTextNode(
        'no matching workflows'));
    this.containerEl.appendChild(this.noResultsDiv);

    //no selected wf div, not added explicitly
    this.noSelectionDiv = document.createElement('div');
    this.noSelectionDiv.className = 'wfSelectionHint';
    this.noSelectionDiv.innerHTML =
        '<div><span>click the design tab to design a new workflow' +
        '</span></div><div><span>' +
        'or find and click on a workflow to view it here</span></div>';

    this.listingEl = document.createElement('div');
    this.listingEl.className = 'workflowListing';

    this.loading = new YAHOO.ccgyabi.widget.Loading(this.listingEl);
    this.loading.show();

    this.containerEl.appendChild(this.listingEl);

    this.hydrate();
  }

  YabiWorkflowCollection.prototype.changeDateRange = function() {
    var value = Math.floor((this.slider.getValue() - 10) / 40);

    while (this.sliderValueEl.firstChild) {
      this.sliderValueEl.removeChild(this.sliderValueEl.firstChild);
    }

    //util fn
    var dblzeropad = function(number) {
      if (number < 10) {
        number = '0' + number;
      }
      return number;
    };

    var today = new Date();
    var epoch = new Date();
    epoch.setTime(0);

    var filterDate = today;

    if (value === 0) {
      this.sliderValueEl.appendChild(document.createTextNode('today'));
    } else if (value === 1) {
      this.sliderValueEl.appendChild(document.createTextNode('past 7 days'));
      filterDate.setDate(filterDate.getDate() - 7);
    } else if (value === 2) {
      this.sliderValueEl.appendChild(document.createTextNode('past month'));
      filterDate.setMonth(filterDate.getMonth() - 1);
    } else if (value === 3) {
      this.sliderValueEl.appendChild(document.createTextNode('past year'));
      filterDate.setFullYear(filterDate.getFullYear() - 1);
    } else if (value === 4) {
      this.sliderValueEl.appendChild(document.createTextNode('forever'));
      filterDate = epoch;
    }

    this.dateStart = filterDate.getFullYear() + '-' +
        dblzeropad(filterDate.getMonth() + 1) + '-' +
        dblzeropad(filterDate.getDate());

    // reload
    this.hydrate();
  };

  YabiWorkflowCollection.prototype.solidify = function(obj) {
    var tempWorkflow;

    this.payload = obj;

    this.loading.hide();

    var tmpWf;

    //clear out existing items
    while (this.workflows.length > 0) {
      tmpWf = this.workflows.pop();
      this.listingEl.removeChild(tmpWf.el);

      //remove event listeners etc
      tmpWf.destroy();
    }

    //add new items
    for (var index in obj) {
      tempWorkflow = new YabiWorkflowProxy(obj[index], this);

      this.listingEl.appendChild(tempWorkflow.el);

      this.workflows.push(tempWorkflow);

      if (this.loadedWorkflow !== null &&
          tempWorkflow.id == this.loadedWorkflow.workflowId) {
        this.loadedWorkflow.attachProxy(tempWorkflow);
        tempWorkflow.setSelected(true);
      }
    }

    this.filter();
  };


  /**
   * hydrate
   *
   * performs an AJAX json fetch of all the workflow listing details and data
   *
   */
  YabiWorkflowCollection.prototype.hydrate = function() {
    if (!Y.Lang.isUndefined(this.jsTransaction) &&
        this.jsTransaction.isInProgress()) {
      this.jsTransaction.abort();
    }

    var baseURL = appURL + 'ws/workflows/datesearch?start=' + this.dateStart;

    //load json
    var jsUrl, jsCallback;
    jsUrl = baseURL;
    jsCallback = {
      success: this.hydrateResponse,
      failure: this.hydrateResponse,
      argument: [this] };
    var cfg = {
      on: jsCallback,
      'arguments': {
        target: this
      }
    };
    this.jsTransaction = Y.io(jsUrl, cfg);
  };

  YabiWorkflowCollection.prototype.toString = function() {
    return 'tool collection';
  };


  /**
   * filter
   *
   * use the search field to limit visible tools
   */
  YabiWorkflowCollection.prototype.filter = function() {
    var filterVal = this.searchEl.value;
    var statusFilterVal = this.statusFilterValue;
    var visibleCount = 0;

    if (filterVal === '') {
      this.clearFilterEl.style.visibility = 'hidden';
    } else {
      this.clearFilterEl.style.visibility = 'visible';
    }

    for (var index in this.workflows) {
      if (this.workflows[index].matchesFilters(filterVal, statusFilterVal)) {
        this.workflows[index].el.style.display = 'block';
        visibleCount++;
      } else {
        this.workflows[index].el.style.display = 'none';
      }
    }

    if (visibleCount > 0) {
      this.noResultsDiv.style.display = 'none';
    } else {
      this.noResultsDiv.style.display = 'block';
    }
  };


  /**
   * clearFilter
   */
  YabiWorkflowCollection.prototype.clearFilter = function() {
    this.searchEl.value = '';
    this.filter();
  };


  /**
   * statusFilter
   */
  YabiWorkflowCollection.prototype.statusFilter = function(value, el) {
    this.statusFilterValue = value;

    //change classes on the filter spans
    for (var index in this.statusEls) {
      this.statusEls[index].className = 'statusFilter';
    }
    el.className = 'selectedStatusFilter';

    this.filter();
  };

  YabiWorkflowCollection.prototype.select = function(id) {
    this.noSelectionDiv.style.display = 'none';

    if (this.loadedWorkflow !== null) {
      this.loadedWorkflow.destroy();
    }

    this.loadedWorkflow = new YabiWorkflow(false);
    this.loadedWorkflow.hydrate(id);
    this.loadedWorkflowEl.appendChild(this.loadedWorkflow.mainEl);
    this.loadedWorkflowOptionsEl.appendChild(this.loadedWorkflow.optionsEl);
    this.loadedWorkflowFileOutputsEl.appendChild(
        this.loadedWorkflow.fileOutputsEl);
    this.loadedWorkflowStatusEl.appendChild(this.loadedWorkflow.statusEl);

    for (var i in this.workflows) {
      if (this.workflows[i].id == id) {
        this.workflows[i].setSelected(true);
        //attach this proxy to the loaded workflow
        this.loadedWorkflow.attachProxy(this.workflows[i]);
      } else {
        this.workflows[i].setSelected(false);
      }
    }

    if (this.onSelectionCallback !== null) {
      this.onSelectionCallback();
    }
  };

  // ------- callback methods, these require a target via their inputs ------


  /**
   * filterCallback
   *
   */
  YabiWorkflowCollection.prototype.filterCallback = function(e, target) {
    target.filter();
  };


  /**
   * statusFilterCallback
   *
   */
  YabiWorkflowCollection.prototype.statusFilterCallback = function(e, invoker) {
    invoker.target.statusFilter(invoker.value, invoker.el);
  };


  /**
   * clearFilterCallback
   *
   */
  YabiWorkflowCollection.prototype.clearFilterCallback = function(e, target) {
    target.clearFilter();
  };


  /**
   * selectWorkflowCallback
   *
   * callback for selecting a workflow proxy object (and hence,
   * loading the workflow)
   */
  YabiWorkflowCollection.prototype.selectWorkflowCallback = function(
      e, invoker) {
    invoker.wfCollection.select(invoker.id);
  };


  /**
   * hydrateResponse
   *
   * handle the response
   * parse json, store internally
   */
  YabiWorkflowCollection.prototype.hydrateResponse = function(
      transId, o, args) {
    var i, json;

    try {
      json = o.responseText;

      target = args.target;

      target.solidify(Y.JSON.parse(json));
    } catch (e) {
      YAHOO.ccgyabi.widget.YabiMessage.handleResponse(o);
      target.solidify([]);
    }
  };

}); // end of YUI().use(...

