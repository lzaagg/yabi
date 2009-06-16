// $Id: YabiJobParam.js 4322 2009-03-17 06:18:36Z ntakayama $

/**
 * YabiJobParam
 * create a new yabi job param corresponding to a tool param
 */
function YabiJobParam(job, obj, allowsBatching, editable, preloadValue) {
    this.job = job;
    this.payload = obj;
    this.isInputFile = false;
    this.isOutputFile = false;
    this.allowsBatching = allowsBatching;
    this.valid = false;
    this.filterGroupHash = [];
    this.switchName = obj["switch"];
    this.defaultValue = obj.value;
    this.subscribedParams = []; //these params change when this param changes
    this.consumableFiles = []; //items that could be consumed
    this.consumedFiles = []; //actual items consumed. unless allowsBatching = true then this will only be one file
    this.isMandatory = true;
    this.editable = editable;
    
    this.displayName = obj.displayName;
    if (! obj.hasOwnProperty("displayName")) {
        this.displayName = obj["switch"];
    }
    
    if (preloadValue !== null) {
        this.defaultValue = preloadValue;
    }
    
    this.value = this.defaultValue;

    this.containerEl = document.createElement('div');

    if (this.payload.mandatory !== true) {
        this.containerEl.style.display = "none";
        this.isMandatory = false;
    }
    
    if (this.payload.inputFile == "yes") {
        this.isInputFile = true;
    }
    
    if (this.payload.outputFile == "yes") {
        this.isOutputFile = true;
    }

    //default to input
    this.renderMode = "input";
    
    //work out how to render inputfile input elements
    if (this.isInputFile) {
        if (this.job.acceptsInput === true) {
            this.renderMode = "select";
        } else {
            this.renderMode = "fileselector";
        }
    } 
    
    //or if not editable, make it a div
    if (!this.editable) {
        this.renderMode = "viewonly";
        this.containerEl.appendChild(document.createTextNode(this.displayName + " = " + this.defaultValue));
        return;
    }
    
    var key;
    
    //some parameters accept multiple possibleValues
    //render as a select
    if (this.payload.possibleValues) {
        this.renderMode = "select";
        
        //possible sub-elements are 'values' or 'filterGroup'
        if (this.payload.possibleValues.value) {
            //coerce single values into an array
            if (!YAHOO.lang.isArray(this.payload.possibleValues.value)) {
                this.possibleValues = [this.payload.possibleValues.value];
            }
            
            this.possibleValues = this.payload.possibleValues.value;
        }
        
        if (this.payload.possibleValues.filterGroup) {
            key = "";
            if (this.payload.possibleValues.filteredBySwitch) {
                key = this.job.paramValue(this.payload.possibleValues.filteredBySwitch);
            }
        
            if (!YAHOO.lang.isArray(this.payload.possibleValues.filterGroup)) {
                this.payload.possibleValues.filterGroup = [this.payload.possibleValues.filterGroup];
            }
            
            for (var index in this.payload.possibleValues.filterGroup) {
                this.filterGroupHash[this.payload.possibleValues.filterGroup[index].key] = this.payload.possibleValues.filterGroup[index];
            }
            
            //set default
            this.possibleValues = this.filterGroupHash[key].value;
            if (preloadValue === null) {
                this.defaultValue = this.filterGroupHash[key]["default"];
            }
            
            //subscribe
            if (this.payload.possibleValues.filteredBySwitch && this.job.getParam(this.payload.possibleValues.filteredBySwitch)) {
                this.job.getParam(this.payload.possibleValues.filteredBySwitch).addSubscriber(this);
            }
        }
    }
    
    //___LABEL EL___
    this.labelEl = document.createElement('label');
    if (this.payload.mandatory === true) {
        this.labelEl.appendChild(document.createTextNode("* "));
    }
    this.labelEl.appendChild(document.createTextNode(this.displayName));
    this.containerEl.appendChild(this.labelEl);
    
    //___INPUT EL___
    if (this.renderMode == "select") {
        this.inputEl = this.renderSelect(true);
    } else if (this.renderMode == "input") {
        this.inputEl = document.createElement('input');
        this.inputEl.value = this.defaultValue;
        this.inputEl.style.width = "180px";
    } else if (this.renderMode == "fileselector") {
        this.fileSelector = new YabiFileSelector(this);
        this.inputEl = this.fileSelector.containerEl;
    }
    this.containerEl.appendChild(this.inputEl);
    
    //accepted extensions
    var ael = this.payload.acceptedExtensionList;
    
    this.acceptedExtensionList = new YabiAcceptedExtensionList(ael);
    this.acceptedExtensionList.allowsBatching = this.allowsBatching;
    this.containerEl.appendChild(this.acceptedExtensionList.containerEl);
    
    //attach key events for changes/keypresses
    YAHOO.util.Event.addListener(this.inputEl, "blur", this.userValidate, this);
    YAHOO.util.Event.addListener(this.inputEl, "keyup", this.userValidate, this);
    YAHOO.util.Event.addListener(this.inputEl, "change", this.userValidate, this);
    
    //run an initial validation on the default value
    this.validate();
}

/**
 * destroy
 *
 * purges event handlers, deletes dom related things that need to be cleared out
 */
YabiJobParam.prototype.destroy = function() {
    YAHOO.util.Event.purgeElement(this.inputEl);
};

/**
 * hasChanged
 *
 * identifies if this value has changed from the default or preloaded value
 */
YabiJobParam.prototype.hasChanged = function() {
    //default value is stored in the payload
    if (this.defaultValue != this.getValue()) {
        return true;
    }
    return false;
};

/**
 * toggleDisplay
 *
 * hides or shows this parameter from view
 */
YabiJobParam.prototype.toggleDisplay = function(shouldDisplay) {
    //mandatory params are always shown
    if (this.payload.mandatory === true) {
        return;
    }
    
    if (shouldDisplay) {
        this.containerEl.style.display = "block";
    } else {
        this.containerEl.style.display = "none";
    }
};

/**
 * emittedFiles
 *
 * if this parameter represents an inputFile or outputFile, then emit a file array
 */
YabiJobParam.prototype.emittedFiles = function() {
    var value = this.getValue();
    
    if ( (this.isInputFile) && (value !== "") ) {
        if (YAHOO.lang.isArray(value)) {
            return value;
        } else {
            return [value];
        }
    } else {
        return [];
    }
};

/**
 * updatePossibleValues
 *
 * update the select drop-down with values, based on the possibleValues json element
 */
YabiJobParam.prototype.updatePossibleValues = function(key) {
    //set default
    this.possibleValues = this.filterGroupHash[key].value;
    this.defaultValue = this.filterGroupHash[key]["default"];
    
    var inEl = this.renderSelect(true);
    this.containerEl.replaceChild(inEl, this.inputEl);
    this.inputEl = inEl;
    
    this.validate();
};

/**
 * optionallyConsumeFiles
 *
 * given an array of files, filter them down to a set of files that are acceptable and render them in a drop-down
 * if the current value hasChanged from the default, then try to retain that selection
 * if not, choose the last valid option automatically as a pre-fill
 */
YabiJobParam.prototype.optionallyConsumeFiles = function(fileArray) {
    var updatedConsumable, updatedConsumed, a, b, index, counter, opt;

    //we can only consume files if we are an input param for a job that accepts inputs
    if (this.isInputFile && this.job.acceptsInput) {
        //console.log(this.job + " .. " + fileArray + " >> " + this.consumableFiles + " >> " + this.consumedFiles);
    
        //first pass, validate that currently consumable/consumed items are still valid
        updatedConsumable = [];
        updatedConsumed = [];
        for (index in this.consumableFiles) {
            for (var subindex in fileArray) {
                a = this.consumableFiles[index];
                b = fileArray[subindex];
                if (a.isEqual(b)) {
                    updatedConsumable.push(a); //retain this item
                    
                    //check if it is currently consumed
                    //console.log(this.consumedFiles);
                    for (var consumeIndex in this.consumedFiles) {
                        //console.log(consumeIndex);
                        if (this.consumedFiles[consumeIndex].isEqual(b)) {
                            updatedConsumed.push(a);
                            break;
                        }
                    }
                    
                    break;
                }
            }
        }
        this.consumableFiles = updatedConsumable.slice(); //this is the new list of items already consumable
        this.consumedFiles = updatedConsumed.slice(); //new list of valid consumed files

        //second pass, if we have no inputs now (old consumable items are all invalid or didn't exist), add new ones
        this.consumableFiles = [];
        for (index in fileArray) {
            if (this.acceptedExtensionList.validForValue(fileArray[index])) {
                this.consumableFiles.push(fileArray[index]);
            }
        }

        //console.log(this.job + " .. " + fileArray + " >> " + this.consumableFiles + " >> " + this.consumedFiles);
       
        //render consumable files
        if (this.renderMode == "select") {
            //purge existing options
            while (this.inputEl.firstChild) {
                this.inputEl.removeChild(this.inputEl.firstChild);
            }
            
            //if non-mandatory, insert a blank value
            if (this.payload.mandatory !== true) {
                opt = document.createElement('option');
                opt.setAttribute("value", "");
                
                if (this.consumedFiles.length === 0) {
                    opt.setAttribute("selected", "true");
                }
                
                this.inputEl.appendChild(opt);
            }

            counter = 1;        
            for (index in this.consumableFiles) {
                opt = document.createElement('option');
                opt.setAttribute("value", ""+this.consumableFiles[index]);
                
                //since we only allow one selection, check for that item
                if (this.consumedFiles.length > 0 && this.consumedFiles[0].isEqual(this.consumableFiles[index])) {
                    opt.setAttribute("selected", "true");
                }
                
                if (this.payload.mandatory === true) {
                    if (this.consumedFiles.length === 0 && this.consumableFiles.length == counter++) {
                        opt.setAttribute("selected", "true");
                    }
                }
        
                opt.appendChild(document.createTextNode(""+this.consumableFiles[index]));
                this.inputEl.appendChild(opt);
            }
        }
        
        //update value of consumedFiles if it is no longer valid
        if (this.consumedFiles.length === 0) {
            if (this.payload.mandatory === true) {
                //default to just selecting the last valid option
                this.consumedFiles = this.consumableFiles.slice(this.consumableFiles.length - 1, 1);
            }
        }
        
        //render consumed files
        if (this.renderMode == "input") {
            this.inputEl.value = this.consumedFiles.toString();
        }

        //finally, validate
        this.validate();
    }
};

/**
 * getValue
 *
 * returns an array or single value that represents the string, file or other input
 */
YabiJobParam.prototype.getValue = function(useInternal) {
    if (useInternal === null) {
        useInternal = false;
    }
    
    if (!this.editable) {
        return this.defaultValue;
    }

    if (this.renderMode == "input") {
        if (this.inputEl.value === "") {
            return "";
        }
    
        if (this.isInputFile) {
            return new YabiJobFileValue(this.job, this.inputEl.value);
        }
        
        return this.inputEl.value;
    } else if (this.renderMode == "select") {
        if (this.inputEl.options.length === 0 || this.inputEl.selectedIndex < 0) {
            return "";
        }
        
        if (this.isInputFile) {
            return this.consumedFiles.slice();
        }
        
        return this.inputEl.options[this.inputEl.selectedIndex].value;
        
    } else if (this.renderMode == "fileselector") {
        return this.fileSelector.getValues(useInternal);
    }
};

/**
 * toJSON
 *
 * interestingly, returns internal values, not emitted values
 * ie file paths are YabiSimpleFileValues, not YabiJobFileValues
 */
YabiJobParam.prototype.toJSON = function() {
    if (!this.hasChanged() && !this.isMandatory) {
        return null;
    }
    
    var values = [];
    var val;
    
    var value = this.getValue(true);
    if (!YAHOO.lang.isArray(value)) {
        value = [value];
    }
    
    for (var index in value) {
        if (!YAHOO.lang.isObject(value[index])) {
            values.push(value[index]);
        } else {
            if (value[index] instanceof YabiSimpleFileValue) {
                values.push(value[index]);
            } else if (value[index] instanceof YabiJob) {
                val = { "type":"job",
                            "jobId":value[index].jobId };
            
                values.push( val );
            } else if (value[index] instanceof YabiJobFileValue) {
                val = { "type":"jobfile",
                            "jobId":value[index].job.jobId,
                            "filename":value[index].filename };
                            
                values.push( val );
            }
        }
    }

    var result = {  "switchName":this.switchName,
                    "valid":this.valid,
                    "value":values };

    return result;
};

/**
 * addSubscriber
 *
 * subscribes one parameter to be notified of changes in value of this parameter
 */
YabiJobParam.prototype.addSubscriber = function(subscriber) {
    this.subscribedParams.push(subscriber);
};

/**
 * validate
 *
 * validate current value
 */
YabiJobParam.prototype.validate = function() {
    //sync this.consumedFiles to the value of the input
    if (this.renderMode == "input") {
        this.consumedFiles = [this.getValue()];
    } else if (this.renderMode == "select") {
        if (this.isInputFile) {
            this.consumedFiles = this.consumableFiles.slice(this.inputEl.selectedIndex, this.inputEl.selectedIndex + 1);
            //console.log(this.consumableFiles);
            //console.log("consumed is now: ")
            //console.log(this.consumedFiles);
            //console.log(" index: " + this.inputEl.selectedIndex);
        } else {
            //dealing with possible values
            
        }
    } else if (this.renderMode == "fileselector") {
        this.consumedFiles = this.getValue();
    }

    this.valid = true;

    //check for empty mandatory
    if (this.payload.mandatory === true && this.getValue().length === 0) {
        //console.log("failed mandatory test");
        //console.log(this.getValue());
        this.valid = false;
    }
    
    //if this is meant to be an input file, validate filetypes
    if (this.isInputFile) {
        //first, verify that consumedFiles exist, if so then we are fine
        if (this.consumedFiles.length === 0) {
            //alternatively, check if the user has manually typed some text that hasn't become a 'consumed file'
            if (!this.acceptedExtensionList.validForValue(this.getValue())) {
                //console.log("failed the valid extension test");
                this.valid = false;
            }
        }
    }
    
    //render internal validation   
    if (!this.valid) {
        if (this.renderMode == "fileselector") {
            this.fileSelector.renderInvalid();
        } else {
            this.inputEl.style.backgroundColor = "red";
            this.inputEl.style.color = "white";
        }
    } else {
        if (this.renderMode == "fileselector") {
            this.fileSelector.renderValid();
        } else {
            this.inputEl.style.backgroundColor = "transparent";
            this.inputEl.style.color = "black";
        }
    }
};

/**
 * renderSelect
 *
 * renders the select element (if there is one)
 */
YabiJobParam.prototype.renderSelect = function(allowDefault) {
    var selectEl = document.createElement('select');
    selectEl.style.width = "180px";
    var option;
    
    //render possibleValues
    if (!this.isInputFile && this.possibleValues) {
        for (var index in this.possibleValues) {
            option = document.createElement("option");
            option.setAttribute("value", this.possibleValues[index].value);
            
            if (this.possibleValues[index].type && this.possibleValues[index].type == "group") {
                option.setAttribute("disabled", "true");
                option.appendChild(document.createTextNode(this.possibleValues[index].display));
            } else {
                option.appendChild(document.createTextNode("   "));
                option.appendChild(document.createTextNode(this.possibleValues[index].display));
            }
            
            if (allowDefault && this.possibleValues[index].value == this.defaultValue) {
                option.setAttribute("selected", "true");
            }
            
            selectEl.appendChild(option);
        }    
    }
    
    return selectEl;
};

// --------- callback methods, these require a target via their inputs --------

/**
 * userValidate
 *
 * fires on user intervention
 */
YabiJobParam.prototype.userValidate = function(e, obj) {
    obj.validate();

    //propagate to subscribed params
    for (var index in obj.subscribedParams) {
        obj.subscribedParams[index].updatePossibleValues(obj.getValue());
    }

    //notify job of validation, propagating the validation from top to bottom
    obj.job.checkValid(true);
};
