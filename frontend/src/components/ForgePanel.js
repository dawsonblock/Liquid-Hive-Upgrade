import { jsx as _jsx, Fragment as _Fragment, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from 'react';
import { 
    Box, Button, Grid, Paper, Switch, FormControlLabel, Typography, 
    Table, TableHead, TableRow, TableCell, TableBody, CircularProgress, 
    Stack, Slider, TextField, Chip, Alert, Divider, Card, CardContent,
    LinearProgress, Accordion, AccordionSummary, AccordionDetails
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { getAdaptersState, promoteAdapter, getGovernor, setGovernor, startTraining } from '../services/api';

const ForgePanel = () => {
    const [adapters, setAdapters] = useState({ state: {} });
    const [gov, setGov] = useState({});
    const [loadingTrain, setLoadingTrain] = useState(false);
    const [trainStatus, setTrainStatus] = useState(null);
    
    // DS-Router configuration state
    const [dsRouterConfig, setDsRouterConfig] = useState({
        conf_threshold: 0.62,
        support_threshold: 0.55,
        max_cot_tokens: 6000
    });
    const [providers, setProviders] = useState({});
    const [budgetStatus, setBudgetStatus] = useState(null);
    const [configSaving, setConfigSaving] = useState(false);
    
    const refresh = async () => {
        try {
            setAdapters(await getAdaptersState());
            setGov(await getGovernor());
            
            // Fetch DS-Router status
            const providersRes = await fetch('/api/providers');
            if (providersRes.ok) {
                setProviders(await providersRes.json());
            }
        }
        catch { }
    };
    
    useEffect(() => { refresh(); }, []);
    
    const onPromote = async (role) => {
        await promoteAdapter(role);
        await refresh();
    };
    
    const onToggleGov = async (key, value) => {
        const enabled = key === 'ENABLE_ORACLE_REFINEMENT' ? value : !!gov.ENABLE_ORACLE_REFINEMENT;
        const force = key === 'FORCE_GPT4O_ARBITER' ? value : !!gov.FORCE_GPT4O_ARBITER;
        await setGovernor(enabled, force);
        await refresh();
    };
    
    const onTrain = async () => {
        setLoadingTrain(true);
        setTrainStatus(null);
        const res = await startTraining();
        if (res.status === 'success')
            setTrainStatus(`New adapter at ${res.adapter_path}`);
        else
            setTrainStatus('Training error: ' + res.detail);
        setLoadingTrain(false);
        await refresh();
    };
    
    const updateRouterConfig = async () => {
        setConfigSaving(true);
        try {
            const response = await fetch('/api/admin/router/set-thresholds', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(dsRouterConfig)
            });
            if (response.ok) {
                setTrainStatus('DS-Router configuration updated successfully');
            } else {
                setTrainStatus('Failed to update DS-Router configuration');
            }
        } catch (error) {
            setTrainStatus('Error updating configuration: ' + error.message);
        }
        setConfigSaving(false);
    };
    
    const resetBudget = async () => {
        try {
            const response = await fetch('/api/admin/budget/reset', {
                method: 'POST'
            });
            if (response.ok) {
                setTrainStatus('Daily budget reset successfully');
                refresh();
            } else {
                setTrainStatus('Failed to reset budget');
            }
        } catch (error) {
            setTrainStatus('Error resetting budget: ' + error.message);
        }
    };
    
    const getProviderStatusColor = (provider) => {
        if (!provider) return 'default';
        if (provider.status === 'healthy') return 'success';
        if (provider.status === 'degraded') return 'warning';
        return 'error';
    };
    
    const getCircuitState = (provider) => {
        return provider?.circuit_state || 'unknown';
    };
    
    const rows = Object.entries(adapters.state || {});
    const providerEntries = Object.entries(providers?.providers || {});
    
    return (
        _jsxs(Grid, { container: true, spacing: 2, children: [
            // DS-Router Control Panel
            _jsx(Grid, { item: true, xs: 12, children: 
                _jsx(Accordion, { defaultExpanded: true, children: [
                    _jsx(AccordionSummary, { expandIcon: _jsx(ExpandMoreIcon, {}), children:
                        _jsx(Typography, { variant: "h6", children: "🧠 DS-Router Intelligence Control" })
                    }),
                    _jsx(AccordionDetails, { children:
                        _jsxs(Grid, { container: true, spacing: 2, children: [
                            // Configuration Controls
                            _jsx(Grid, { item: true, xs: 12, md: 6, children:
                                _jsxs(Card, { children: [
                                    _jsx(CardContent, { children: 
                                        _jsxs(Stack, { spacing: 2, children: [
                                            _jsx(Typography, { variant: "subtitle1", children: "Routing Thresholds" }),
                                            _jsxs(Box, { children: [
                                                _jsx(Typography, { gutterBottom: true, children: `Confidence Threshold: ${dsRouterConfig.conf_threshold}` }),
                                                _jsx(Slider, {
                                                    value: dsRouterConfig.conf_threshold,
                                                    onChange: (e, value) => setDsRouterConfig({...dsRouterConfig, conf_threshold: value}),
                                                    min: 0.1,
                                                    max: 1.0,
                                                    step: 0.01,
                                                    valueLabelDisplay: "auto"
                                                })
                                            ]}),
                                            _jsxs(Box, { children: [
                                                _jsx(Typography, { gutterBottom: true, children: `RAG Support Threshold: ${dsRouterConfig.support_threshold}` }),
                                                _jsx(Slider, {
                                                    value: dsRouterConfig.support_threshold,
                                                    onChange: (e, value) => setDsRouterConfig({...dsRouterConfig, support_threshold: value}),
                                                    min: 0.1,
                                                    max: 1.0,
                                                    step: 0.01,
                                                    valueLabelDisplay: "auto"
                                                })
                                            ]}),
                                            _jsxs(Box, { children: [
                                                _jsx(Typography, { gutterBottom: true, children: `Max CoT Tokens: ${dsRouterConfig.max_cot_tokens}` }),
                                                _jsx(Slider, {
                                                    value: dsRouterConfig.max_cot_tokens,
                                                    onChange: (e, value) => setDsRouterConfig({...dsRouterConfig, max_cot_tokens: value}),
                                                    min: 1000,
                                                    max: 10000,
                                                    step: 500,
                                                    valueLabelDisplay: "auto"
                                                })
                                            ]}),
                                            _jsx(Button, {
                                                variant: "contained",
                                                onClick: updateRouterConfig,
                                                disabled: configSaving,
                                                children: configSaving ? _jsx(CircularProgress, { size: 20 }) : "Update Configuration"
                                            })
                                        ]})
                                    })
                                ]})
                            }),
                            
                            // Provider Status
                            _jsx(Grid, { item: true, xs: 12, md: 6, children:
                                _jsxs(Card, { children: [
                                    _jsx(CardContent, { children:
                                        _jsxs(Stack, { spacing: 2, children: [
                                            _jsx(Typography, { variant: "subtitle1", children: "Provider Health Status" }),
                                            ...providerEntries.map(([name, provider]) => 
                                                _jsxs(Box, { 
                                                    key: name,
                                                    display: 'flex', 
                                                    justifyContent: 'space-between', 
                                                    alignItems: 'center',
                                                    children: [
                                                        _jsx(Typography, { variant: "body2", children: name }),
                                                        _jsxs(Stack, { direction: 'row', spacing: 1, children: [
                                                            _jsx(Chip, { 
                                                                label: provider.status || 'unknown',
                                                                color: getProviderStatusColor(provider),
                                                                size: 'small'
                                                            }),
                                                            _jsx(Chip, {
                                                                label: `CB: ${getCircuitState(provider)}`,
                                                                variant: 'outlined',
                                                                size: 'small'
                                                            })
                                                        ]})
                                                    ]
                                                })
                                            ),
                                            _jsx(Button, {
                                                variant: "outlined",
                                                onClick: resetBudget,
                                                color: "warning",
                                                children: "Reset Daily Budget"
                                            })
                                        ]})
                                    })
                                ]})
                            })
                        ]})
                    })
                ]})
            }),
            
            // Oracle/Arbiter Control Panel
            _jsx(Grid, { item: true, xs: 12, children: 
                _jsx(Accordion, { children: [
                    _jsx(AccordionSummary, { expandIcon: _jsx(ExpandMoreIcon, {}), children:
                        _jsx(Typography, { variant: "h6", children: "⚡ Oracle/Arbiter Pipeline" })
                    }),
                    _jsx(AccordionDetails, { children:
                        _jsxs(Paper, { variant: "outlined", sx: { p: 2 }, children: [
                            _jsxs(Stack, { direction: "row", spacing: 2, alignItems: "center", children: [
                                _jsx(FormControlLabel, { 
                                    control: _jsx(Switch, { 
                                        checked: !!gov.ENABLE_ORACLE_REFINEMENT, 
                                        onChange: e => onToggleGov('ENABLE_ORACLE_REFINEMENT', e.target.checked) 
                                    }), 
                                    label: "Enable Oracle Refinement" 
                                }),
                                _jsx(FormControlLabel, { 
                                    control: _jsx(Switch, { 
                                        checked: !!gov.FORCE_GPT4O_ARBITER, 
                                        onChange: e => onToggleGov('FORCE_GPT4O_ARBITER', e.target.checked) 
                                    }), 
                                    label: "Force GPT‑4o Arbiter" 
                                }),
                                _jsx(Box, { flexGrow: 1 }),
                                _jsx(Button, { 
                                    variant: "contained", 
                                    color: "secondary", 
                                    onClick: onTrain, 
                                    disabled: loadingTrain, 
                                    children: loadingTrain ? 
                                        _jsxs(_Fragment, { children: [
                                            _jsx(CircularProgress, { size: 18, sx: { mr: 1 } }), 
                                            "Igniting..."
                                        ]}) : 
                                        'Ignite Training Cycle' 
                                })
                            ]})
                        ]})
                    })
                ]})
            }),
            
            // Adapter Management
            _jsx(Grid, { item: true, xs: 12, children: 
                _jsx(Accordion, { children: [
                    _jsx(AccordionSummary, { expandIcon: _jsx(ExpandMoreIcon, {}), children:
                        _jsx(Typography, { variant: "h6", children: "🔄 Adapter Deployment Manager" })
                    }),
                    _jsx(AccordionDetails, { children:
                        _jsxs(Paper, { variant: "outlined", sx: { p: 2 }, children: [
                            _jsxs(Table, { size: "small", children: [
                                _jsx(TableHead, { children: 
                                    _jsxs(TableRow, { children: [
                                        _jsx(TableCell, { children: "Role" }),
                                        _jsx(TableCell, { children: "Champion" }),
                                        _jsx(TableCell, { children: "Challenger" }),
                                        _jsx(TableCell, { align: "right", children: "Action" })
                                    ]})
                                }),
                                _jsxs(TableBody, { children: [
                                    ...rows.map(([role, entry]) => (
                                        _jsxs(TableRow, { children: [
                                            _jsx(TableCell, { children: role }),
                                            _jsx(TableCell, { children: entry.active || '' }),
                                            _jsx(TableCell, { children: entry.challenger || '' }),
                                            _jsx(TableCell, { align: "right", children: 
                                                _jsx(Button, { 
                                                    variant: "outlined", 
                                                    size: "small", 
                                                    onClick: () => onPromote(role), 
                                                    disabled: !entry.challenger, 
                                                    children: "Promote to Champion" 
                                                })
                                            })
                                        ]}, role)
                                    )),
                                    rows.length === 0 && (
                                        _jsx(TableRow, { children: 
                                            _jsx(TableCell, { colSpan: 4, children: 
                                                _jsx(Typography, { variant: "body2", color: "text.secondary", children: "No adapters registered." })
                                            })
                                        })
                                    )
                                ]})
                            ]})
                        ]})
                    })
                ]})
            }),
            
            // Status Messages
            trainStatus && _jsx(Grid, { item: true, xs: 12, children:
                _jsx(Alert, { 
                    severity: trainStatus.includes('error') || trainStatus.includes('Failed') ? 'error' : 'success',
                    children: trainStatus 
                })
            })
        ]})
    );
};

export default ForgePanel;
