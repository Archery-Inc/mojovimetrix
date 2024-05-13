/**
 * File: valuegraph.js
 * Project: Jovimetrix
 *
 */

import { app } from "../../../scripts/app.js"
import { node_add_dynamic } from '../util/util.js'
import { api_cmd_jovian } from '../util/util_api.js'

const _id = "VALUE GRAPH (JOV) 📈"
const _prefix = '❔'

app.registerExtension({
	name: 'jovimetrix.node.' + _id,
    init() {
        LGraphCanvas.link_type_colors['JOV_VG_0'] = "#A00";
        LGraphCanvas.link_type_colors['JOV_VG_1'] = "#0A0";
        LGraphCanvas.link_type_colors['JOV_VG_2'] = "#00A";
        LGraphCanvas.link_type_colors['JOV_VG_3'] = "#0AA";
        LGraphCanvas.link_type_colors['JOV_VG_4'] = "#AA0";
        LGraphCanvas.link_type_colors['JOV_VG_5'] = "#A0A";
        LGraphCanvas.link_type_colors['JOV_VG_6'] = "#000";
    },
	async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== _id) {
            return;
        }
        nodeType = node_add_dynamic(nodeType, _prefix, "*", 7);
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = async function () {
            const me = onNodeCreated?.apply(this);
            const self = this;
            const widget_reset = this.widgets.find(w => w.name === 'RESET');
            widget_reset.callback = async (e) => {
                widget_reset.value = false;
                api_cmd_jovian(self.id, "reset");
            }
            return me;
        }

        const onConnectionsChange = nodeType.prototype.onConnectionsChange
        nodeType.prototype.onConnectionsChange = function (slotType, slot, event, link_info, data) {
            const me = onConnectionsChange?.apply(this, arguments);
            if (!link_info || slot == this.inputs.length) {
                return;
            }
            for (let i = 0; i < this.inputs.length; i++) {
                const link_id = this.inputs[i].link;
                const link = app.graph.links[link_id];
                if(link) {
                    link.type = `JOV_VG_${i}`;
                    this.inputs[i].color_on = LGraphCanvas.link_type_colors[link.type];
                }
            }
            app.graph.setDirtyCanvas(true, true);
            return me;
        }
	}
})
