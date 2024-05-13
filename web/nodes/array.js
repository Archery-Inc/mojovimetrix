/**
 * File: batcher.js
 * Project: Jovimetrix
 *
 */

import { app } from "../../../scripts/app.js"
import { fitHeight, node_add_dynamic } from '../util/util.js'
import { widget_hide, widget_show } from '../util/util_widget.js'

const _id = "ARRAY (JOV) 📚"
const _prefix = '❔'

app.registerExtension({
	name: 'jovimetrix.node.' + _id,
	async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== _id) {
            return;
        }
        nodeType = node_add_dynamic(nodeType, _prefix);
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = async function () {
            const me = onNodeCreated?.apply(this);
            const widget_idx = this.widgets.find(w => w.name === 'INDEX');
            const widget_range = this.widgets.find(w => w.name === 'RANGE');
            const widget_str = this.widgets.find(w => w.name === '📝');
            const widget_seed = this.widgets.find(w => w.name === 'SEED');
            const widget_mode = this.widgets.find(w => w.name === 'MODE');
            widget_mode.callback = async () => {
                widget_hide(this, widget_idx);
                widget_hide(this, widget_range);
                widget_hide(this, widget_str);
                widget_hide(this, widget_seed);
                if (widget_mode.value == "PICK") {
                    widget_show(widget_idx);
                } else if (widget_mode.value == "SLICE") {
                    widget_show(widget_range);
                } else if (widget_mode.value == "INDEX_LIST") {
                    widget_show(widget_str);
                } else if (widget_mode.value == "RANDOM") {
                    widget_show(widget_seed);
                } else {
                    // MERGE

                }
                fitHeight(this);
            }
            setTimeout(() => { widget_mode.callback(); }, 10);
            return me;
        }
	}
})
