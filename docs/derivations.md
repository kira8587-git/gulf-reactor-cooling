# Formulae and derivations

Step-by-step derivations of the model's equations (sections F1–F6), for anyone who wants to check the maths behind `model/`.

## F1. The four equations

**(1) Energy balance.** First law for the whole plant:

$$\dot Q_c = \dot Q_{\rm th} - \frac{P}{\eta_g} = 4000 - \frac{1425.3}{0.985} = 2553\ \text{MW}$$

**(2) Condenser.**

$$T_c = T_s + \frac{\dot Q_c}{\varepsilon\,\dot m\,c_p}, \qquad \varepsilon = 1 - e^{-UA/(\dot m c_p)}$$

**(3) Last turbine stage.** $g$ is the energy per kg the steam has not turned into work:

$$P = P_{\rm ref} - \eta_g\,\dot m_{\rm ex}\,\big[g(p_e) - g(p_{\rm ref})\big], \qquad g(p) = h_e(p) + \frac{V^2}{2}, \qquad V = \frac{\dot m_{\rm ex}\,v_e(p)}{A_{\rm ex}}$$

$$h_e(p) = h_{\rm in} - \eta_{\rm LP}\big[h_{\rm in} - h(p, s_{\rm in})\big]$$

**(4) Choke.**

$$p_e = \max(p_c,\ p^*), \qquad p^* = \arg\min_p\ g(p) = 3.90\ \text{kPa}$$

That is a condenser at 28.5 °C, a sea at $T^* = 19.3$ °C.

## F2. Deriving the condenser equation, and Clausius–Clapeyron

**Condenser.** Steam condenses at one temperature $T_c$. Water at temperature $T$ in a small piece of tube area $\mathrm dA$ gains heat in proportion to $(T_c - T)$ (Newton's law of cooling):

$$\dot m\,c_p\,\mathrm dT = U\,(T_c - T)\,\mathrm dA$$

Separate the variables and integrate from the inlet ($T_s$) to the outlet:

$$\int_{T_s}^{T_{\rm out}} \frac{\mathrm dT}{T_c - T} = \frac{UA}{\dot m c_p} \quad\Rightarrow\quad \frac{T_c - T_{\rm out}}{T_c - T_s} = e^{-UA/(\dot m c_p)}$$

So the water's rise is a fixed fraction of the gap, $\Delta T_w = \varepsilon\,(T_c - T_s)$. With $\Delta T_w = \dot Q_c/(\dot m c_p)$ this is eq. (2).

**Check.** $\dot m = 102{,}770$ kg/s and $c_p = 3968$ J/(kg K) give $\Delta T_w = 6.26$ K. The design gap of 9.4 K gives $\varepsilon = 0.666$.

**Clausius–Clapeyron.** The condenser pressure is the vapour pressure at $T_c$. Run a tiny Carnot cycle with 1 kg of water between $T$ and $T - \mathrm dT$: heat in is $h_{fg}$, work is $v_{fg}\,\mathrm dp$, efficiency is $\mathrm dT/T$. So

$$\frac{v_{fg}\,\mathrm dp}{h_{fg}} = \frac{\mathrm dT}{T} \quad\Rightarrow\quad \frac{\mathrm dp}{\mathrm dT} = \frac{h_{fg}}{T\,v_{fg}} = \frac{2398}{316.5 \times 16.55} = 0.458\ \text{kPa/K}$$

## F3. Deriving the choke

Output is largest when $g(p) = h_e + V^2/2$ is smallest.

**Enthalpy part.** For an ideal adiabatic expansion, $\mathrm dh = T\,\mathrm ds + v\,\mathrm dp$ with $\mathrm ds = 0$, so $\mathrm dh = v\,\mathrm dp$. A real stage achieves a fraction $\eta_{\rm LP}$:

$$\frac{\mathrm dh_e}{\mathrm dp} = \eta_{\rm LP}\,v_s$$

**Kinetic part.** By continuity $V \propto v_e$. With $\kappa = -\mathrm d\ln p/\mathrm d\ln v_e$:

$$\frac{\mathrm d}{\mathrm dp}\Big(\frac{V^2}{2}\Big) = \frac{V^2}{v_e}\frac{\mathrm dv_e}{\mathrm dp} = -\frac{V^2}{\kappa\,p}$$

**Together.**

$$\frac{\mathrm dg}{\mathrm dp} = \eta_{\rm LP}v_s - \frac{V^2}{\kappa p} = \eta_{\rm LP}\,v_s\,\big(1 - M^2\big), \qquad M^2 = \frac{V^2}{\eta_{\rm LP}\,\kappa\,p\,v_s}$$

At $M = 1$, $\mathrm dg/\mathrm dp = 0$: the minimum of $g$, the choke. The speed of sound in a gas is $c = \sqrt{\gamma p v}$, so $M^2$ has the form $(V/c)^2$. It is an analogy.

**Check.** At 8.8 kPa: $v_s = 13.5$ m³/kg, $V = 154$ m/s, $M^2 = 0.21$. The gain is $11.8 \times (1 - 0.21) = 9.3$ kJ/kg per kPa.

## F4. Deriving the law

Chain rule: output depends on pressure, pressure on condenser temperature.

$$\frac{\mathrm dP}{\mathrm dT_c} = \frac{\mathrm dP}{\mathrm dp}\cdot\frac{\mathrm dp}{\mathrm dT_c} = \Big(-\eta_g\,\dot m_{\rm ex}\frac{\mathrm dg}{\mathrm dp}\Big)\cdot\frac{h_{fg}}{T_c\,v_{fg}}$$

$$\frac{\mathrm dP}{\mathrm dT_c} = -\,\eta_g\,\eta_{\rm LP}\,\dot m_{\rm ex}\,\frac{v_s}{v_{fg}}\,\frac{h_{fg}}{T_c}\,\big(1 - M^2\big) \qquad \text{(eq. 6)}$$

**Check.** $\mathrm dP/\mathrm dp = -0.985 \times 1176 \times 9.33 = -10.8$ MW per kPa; times 0.458 kPa/K gives about $-4.9$ MW per K, 0.35 % of 1,425 MW.

**Relative form.** With $\dot m_{\rm ex}x_e h_{fg} \approx \dot Q_c$, $v_s/v_{fg} \approx x_s$ and $\dot Q_c/P \approx (1-\eta)/\eta$:

$$\sigma = \frac{1}{P}\frac{\mathrm dP}{\mathrm dT_c} \approx -\,\eta_{\rm LP}\,\frac{x_s}{x_e}\,\frac{1-\eta}{\eta}\,\frac{1}{T_c}\,\big(1 - M^2\big) \qquad \text{(eq. 7)}$$

**The simple model is $M = 0$.** $\eta = 0.361$ gives $(1-\eta)/\eta = 1.77$; divided by 313 K: 0.57 % per K; times 0.87 and 0.95: 0.47 % per °C.

## F5. The fit and its statistics

$$S(A_{\rm ex}, L_u) = \sum_{u,m}\Big(P^{\rm obs}_{u,m} - \overline{P^{\rm model}_m}(A_{\rm ex}) + L_u\Big)^2$$

Setting $\partial S/\partial L_u = 0$ gives $L_u = \text{mean}_m\big(\overline{P^{\rm model}_m} - P^{\rm obs}_{u,m}\big)$. $A_{\rm ex}$ is found by a one-variable search.

| Quantity | Value |
|---|---|
| Points / fitted numbers / degrees of freedom | 36 / 5 / 31 |
| RMS error $\sqrt{S/n}$; residual standard deviation $\sqrt{S/31}$ | 3.1 MW; 3.3 MW |
| Within-unit R²; largest miss | 0.97; 6.8 MW |
| Leave one unit out | 3.3 MW |
| Exit area from the design document, only $L_u$ fitted | 5.0 MW |
| Exit area, 95 % bootstrap interval (extra check, not in the report) | about 101–114 m², i.e. 126–176 GWh |
| Real slope | 0.259 ± 0.009 % per °C |
| Straight-line fit, for comparison | 3.4 MW |

## F6. Annual loss, pumping and the 5 °C rule

$$E = \frac{24\,\text{LF}}{N_{\rm years}}\sum_{d}\big[P_{\max} - P(T_{s,d})\big] = 157\ \text{GWh}$$

with LF = 0.784 and $P_{\max} = 1472$ MW. That is 1.55 % of $1472 \times 8760 \times 0.784 = 10{,}110$ GWh.

**Daily decision.**

$$P_{\rm net} = P\big(T_c(\dot V_w)\big) - \frac{\rho g}{\eta_p}\Big[\dot V_w\Big(H_s + H_f\Big(\frac{\dot V_w}{\dot V_{\rm des}}\Big)^2\Big) + \dot V_b H_b\Big], \qquad \frac{\dot Q_c}{\rho c_p(\dot V_w + \dot V_b)} \le 5\ \text{K}$$

**Price of the rule, by hand.** Total flow needed is $\dot V = \dot Q_c/(\rho c_p\,\Delta T)$, so

$$\frac{\mathrm d\dot V}{\mathrm d\Delta T} = -\frac{\dot Q_c}{\rho c_p\,\Delta T^2} = -\frac{2553\times10^6}{1027 \times 3968 \times 25} \approx -25\ \text{m}^3/\text{s per K}$$

Pumping 25 m³/s through 6 m costs $1027 \times 9.81 \times 25 \times 6/0.85 \approx 1.8$ MW per K. The full optimisation gives 1.75–1.79.
