// Run with the Codex bundled Node runtime from a build directory linked to its node_modules.
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { Presentation, PresentationFile } from '@oai/artifact-tool';

const root = process.cwd();
const skill = '/Users/peerawatsomsurat/.codex/plugins/cache/openai-primary-runtime/presentations/26.1007.11041/skills/presentations';
const runtimePython = '/Users/peerawatsomsurat/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3';
const { finalizePresentation, resolvePresentationFont, applyPresentationChartFont } = await import(pathToFileURL(path.join(skill, 'container_tools/artifact_tool_utils.mjs')).href);
const font = resolvePresentationFont({fontFamily: 'Arial'});
const fontPolicy = {basis: 'design', families: [font]};
const read = async file => JSON.parse(await fs.readFile(path.join(root, file), 'utf8'));
const model = await read('reports/model_metadata.json');
const history = await read('reports/training_history.json');
const cost = await read('reports/evidence/cost-summary.json');
let warm; try { warm = await read('reports/evidence/deployed-warm.json'); } catch {}
const deck = Presentation.create({slideSize: {width: 1280, height: 720}});
const ink = '#20312B', muted = '#5A685F', accent = '#35604A';

function text(slide, value, left, top, width, height, size=28, color=ink, bold=false) {
  const shape = slide.shapes.add({geometry:'textbox', position:{left,top,width,height}, fill:'none', line:{fill:'none',width:0}});
  shape.text = value;
  shape.text.style = {typeface:font, fontSize:size, color, bold};
  return shape;
}
function slide(title, note) {
  const item=deck.slides.add(); item.background.fill='#F7F4EE';
  text(item, 'ITCS355  /  GROUP IDEA', 64, 34, 1000, 28, 18, muted, true);
  text(item,title,64,93,1152,100,44,ink,true);
  text(item,`6688218 Peerawat  ·  6688230 Yongyot`,64,666,1040,28,16,muted);
  text(item,String(deck.slides.items.length).padStart(2,'0'),1150,666,65,28,16,muted);
  item.speakerNotes.text=note; return item;
}
function lines(item, values, left=64, top=230, width=1120, size=28, gap=80) {
  values.forEach((value,index)=>text(item,value,left,top+index*gap,width,gap-10,size));
}
const citations='Sources: DATA_LICENSE.md; https://www.kaggle.com/datasets/gpiosenka/coffee-bean-dataset-resized-224-x-224; https://www.kaggle.com/datasets/sot2542/coffee-bean-dataset-v1; https://arxiv.org/abs/2206.01841. Actual release metadata and reports/evidence support measured claims.';

let s=slide('Coffee Bean Roast Classification',`0:00–1:00. State the educational image-level scope and intended user. Green means unroasted. Scope revision needs instructor approval. Show examples and explain that these are licensed validation fixtures. ${citations}`);
text(s,'Visual inspection API  ·  Dark / Green / Light / Medium',64,193,1152,44,28,accent);
for (const [index,label] of model.classes.entries()) {
  const bytes=await fs.readFile(path.join(root,`tests/fixtures/${label}.png`));
  s.images.add({blob:bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),contentType:'image/png',alt:`Licensed ${label} coffee image`,fit:'contain',position:{left:64+index*296,top:290,width:240,height:240}});
  text(s,label,64+index*296,547,240,40,25,ink,true);
}
text(s,'Educational image classification; defects and SCA certification are outside this scope.',64,608,1152,38,21,muted);

s=slide('An audit changed our evaluation',`1:00–2:00. Explain that all400 original test images duplicated original training images. The original99.75% score remains a historical baseline. The corrected manifest enforces zero exact-pixel duplicates, but does not prove group/near-duplicate independence. ${citations}`);
text(s,'1,600 supplied images → 1,194 unique images',64,207,1152,52,34,accent,true);
const dataChart=s.charts.add('bar',{position:{left:64,top:301,width:660,height:303},categories:['Train','Validation','Test'],series:[{name:'Unique images',values:[835,178,181],fill:accent}],hasLegend:false,dataLabels:{showValue:true,position:'outEnd'},yAxis:{majorGridlines:{fill:'#D8DED7',width:1}}});
applyPresentationChartFont(dataChart,{fontFamily:font});
lines(s,['406 duplicate copies removed','All 400 old test images overlapped','Seed 42; fixed four-class order','CC BY-SA 4.0; both sources v1'],780,304,435,25,78);

s=slide('Reproducible training in 22 minutes',`2:00–3:00. Show the actual Git commit, DVC revision, dependency hash and MLflow history in the repository. Keep the model-selection explanation brief: lowest validation loss; compare exports only on validation; evaluate selected release once on test. Twenty epochs took${(model.training_duration_seconds/60).toFixed(2)}minutes, batch8 on Apple M1 MPS. No bitwise determinism claim. Loss chart values are rounded to four decimal places; full precision remains in training_history.json. ${citations}`);
text(s,`Best checkpoint: epoch ${model.best_epoch}  ·  181/181 test images correct`,64,207,1152,52,30,accent,true);
const lossChart=s.charts.add('line',{position:{left:64,top:304,width:716,height:306},categories:history.map(h=>String(h.epoch)),series:[{name:'Training loss',values:history.map(h=>Number(h.train_loss.toFixed(4))),fill:'#A4693C'},{name:'Validation loss',values:history.map(h=>Number(h.validation_loss.toFixed(4))),fill:accent}],hasLegend:true,yAxis:{majorGridlines:{fill:'#D8DED7',width:1}}});
applyPresentationChartFont(lossChart,{fontFamily:font});
lines(s,['ImageNet Swin-T; seed 42','20 epochs; batch 8; locked env','INT8: 29.6 MiB; F1 retained','64.3 ms local export median'],829,305,386,25,78);

s=slide('Build, publish and operate',`3:00–4:00. Walk through the Azure East Asia architecture and registry lineage. The final Linux image is pinned by digest. Runtime managed identity and GitHub OIDC avoid saved cloud secrets. PR validation restores a model instead of training. Candidate endpoint checks and fixed benchmark gates precede traffic promotion; failures restore previous traffic. Sources: https://learn.microsoft.com/azure/container-apps/scale-app; https://learn.microsoft.com/azure/container-apps/managed-identity; reports/evidence/ci-success.json.`);
for(const [index,title] of ['BUILD','PUBLISH','OPERATE'].entries()) text(s,title,64+index*392,239,350,42,25,accent,true);
lines(s,['Git + private Blob DVC','Locked automated training','Immutable model bundle','Azure ML registry lineage'],64,310,350,25,70);
lines(s,['CI data / model / API tests','Linux container integration','Private ACR image digest','Candidate checks → promote'],456,310,350,25,70);
lines(s,['Container Apps East Asia','2 vCPU / 4 GiB; min 0 / max 2','JSON logs + Azure workbook','Camera failure → email alert'],848,310,367,25,70);

s=slide('Live prediction and controlled errors',`4:00–5:00. Submit a real coffee PNG and base64 image. Show four finite probabilities, class IDs0–3 and matching X-Model-Version. Invite unexpected input. API tests and OpenAPI document controlled errors. Do not imply calibrated confidence or automatic noncoffee detection.`);
lines(s,['/predict  ·  raw JPEG/PNG or multipart file','/predict/base64  ·  strict JSON/base64','Four probabilities; fixed IDs; matching model version'],64,228,1152,29,85);
text(s,'400 unreadable  /  413 oversized  /  415 unsupported  /  422 rejected',64,510,1152,48,25,accent,true);
text(s,'5 MiB decoded  ·  20 megapixels  ·  inference concurrency 2',64,575,1152,43,25,muted);

s=slide('We designed a camera failure',`5:00–6:00. Inject black and white frames; show422 before inference, rejection JSON, anomaly counter, local webhook and deployed workbook. Trigger Azure email ahead because its evaluation interval is five minutes. Actual recipient delivery must be evidenced separately from a configured action group. Show guard mutation causes failing regression and deployment prevention. Sources: https://learn.microsoft.com/azure/container-apps/log-monitoring; reports/evidence/local-alert-delivery.log; reports/evidence/optical-regression-drill.json.`);
lines(s,['Covered / overexposed camera → HTTP 422 before inference','Structured rejection log + anomaly counter','Prometheus alert delivered to local webhook','Azure five-minute rule → email action group'],64,236,1152,29,88);
text(s,'Regression: remove the optical guard → tests must fail → release blocked',64,601,1152,43,24,accent,true);

s=slide('Measured performance and the bill',`6:00–7:00. Show deployed warm and cold reports when complete. Explain1000 requests at concurrency2 and20 verifiedzero-replica cold trials. Freeze initialp95/p99 plus20% and enforce fixed targets later. Container bytes are separate. Cost/1000 uses actual wall duration and a conservative configured two-replica allocation bound; it is not an invoice. Registry/storage/monitoring remain chargeable during scale-to-zero. Primary rates and ECB exchange are captured under reports/evidence.`);
lines(s,[warm ? `Warm p95 ${warm.p95_ms.toFixed(1)} ms / p99 ${warm.p99_ms.toFixed(1)} ms` : 'Warm benchmark: pending deployed measurements','20 verified cold starts; fixed targets = measured + 20%',`Remaining allowance: ${cost.budget.remaining_allowance_thb.toFixed(2)} THB`,`Seven-day forecast + margin: ${cost.budget.forecast_thb_including_25_percent_margin.toFixed(2)} THB`],64,231,1152,29,80);
text(s,'Costs reported separately: serving / storage / registry / monitoring / training',64,584,1152,51,24,accent,true);

s=slide('Evidence, limitations and next steps',`7:00–8:00. Show the current requirement checklist and safe teardown receipt. All technical requirements need successful evidence. Instructor scope approval, architecture clinic, live presentation/Q&A and final submission remain external milestones. Proposed team responsibility split must be confirmed by actual contributions. Another week would focus on independent camera/source data, calibration and broader operating-condition checks. Reserve five minutes for questions.`);
lines(s,['Complete evidence is recorded in the requirement checklist','Uncalibrated confidence; source / camera confounding','Uniform-frame guard does not reject every noncoffee image','Next week: independent images and confidence calibration','Academic approval, review, live Q&A and submission remain pending'],64,222,1152,27,80);

const staging=path.join(root,'tmp/slides'); await fs.mkdir(staging,{recursive:true});
for(const [index,item] of deck.slides.items.entries()) {
  const blob=await deck.export({slide:item,format:'png',scale:1});
  await fs.writeFile(path.join(staging,`slide-${index+1}.png`),new Uint8Array(await blob.arrayBuffer()));
}
const candidate=path.join(staging,'candidate.pptx'); await (await PresentationFile.exportPptx(deck)).save(candidate);
const result=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:path.join(root,process.env.SLIDES_OUTPUT || 'deliverables/capstone_slides.pptx'),pythonExecutable:runtimePython,integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],explicitTotalSlideCount:8,requiredNativeChartOwnerSlides:[2,3],materializeLiteralChartWorkbooks:true,fontPolicy,verifyArtifactToolImport:true,receiptPath:path.join(staging,'validation.json')});
console.log(JSON.stringify({finalized:result.finalPath || true,slides:8}));
