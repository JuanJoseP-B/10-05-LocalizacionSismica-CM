import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { useSimulation } from '../store/SimulationContext';
import { colorSensorPorSenal } from '../math/model';

export default function Scene3D() {
  const { params, sensors } = useSimulation();
  const canvasRef = useRef(null);
  const sensorMeshesRef = useRef([]);
  const sourceMeshRef = useRef(null);
  const pulseMeshRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current) return undefined;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, canvasRef.current.clientWidth / canvasRef.current.clientHeight, 0.1, 1000);
    camera.position.set(0, 90, 110);
    const renderer = new THREE.WebGLRenderer({ canvas: canvasRef.current, antialias: true, alpha: true });
    renderer.setSize(canvasRef.current.clientWidth, canvasRef.current.clientHeight);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.maxPolarAngle = Math.PI / 2 - 0.05;
    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    const light = new THREE.PointLight(0xffffff, 1.2);
    light.position.set(100, 120, 100);
    scene.add(light);
    scene.add(new THREE.GridHelper(150, 15, 0x38bdf8, 0x1e293b));

    const sensorGeo = new THREE.SphereGeometry(2.5, 16, 16);
    sensorMeshesRef.current = sensors.map((s) => {
      const mat = new THREE.MeshStandardMaterial({ color: 0x64748b, roughness: 0.2 });
      const mesh = new THREE.Mesh(sensorGeo, mat);
      mesh.position.set(s.x, 0, s.y);
      scene.add(mesh);
      return { id: s.id, mesh, mat };
    });

    const sourceGeo = new THREE.SphereGeometry(4, 32, 32);
    const sourceMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, emissive: 0xf59e0b, emissiveIntensity: 0.8 });
    const sourceMesh = new THREE.Mesh(sourceGeo, sourceMat);
    sourceMesh.position.set(params.x0, -params.z0, params.y0);
    scene.add(sourceMesh);
    sourceMeshRef.current = sourceMesh;

    const pulseGeo = new THREE.SphereGeometry(Math.max(params.A0 / 250, 0.5), 32, 32);
    const pulseMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b, transparent: true, opacity: 0.15, wireframe: true });
    const pulseMesh = new THREE.Mesh(pulseGeo, pulseMat);
    pulseMesh.position.set(params.x0, -params.z0, params.y0);
    scene.add(pulseMesh);
    pulseMeshRef.current = pulseMesh;

    let frameId;
    const clock = new THREE.Clock();
    const animate = () => {
      frameId = requestAnimationFrame(animate);
      controls.update();
      const scale = 1 + Math.sin(clock.getElapsedTime() * 5) * 0.15;
      pulseMesh.scale.set(scale, scale, scale);
      renderer.render(scene, camera);
    };
    animate();

    const onResize = () => {
      if (!canvasRef.current) return;
      camera.aspect = canvasRef.current.clientWidth / canvasRef.current.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(canvasRef.current.clientWidth, canvasRef.current.clientHeight);
    };
    window.addEventListener('resize', onResize);

    return () => {
      cancelAnimationFrame(frameId);
      window.removeEventListener('resize', onResize);
      controls.dispose();
      renderer.dispose();
      sensorGeo.dispose();
      sourceGeo.dispose();
      pulseGeo.dispose();
    };
  }, []);

  useEffect(() => {
    if (sourceMeshRef.current) {
      sourceMeshRef.current.position.set(params.x0, -params.z0, params.y0);
      sourceMeshRef.current.visible = params.A0 > 0;
    }
    if (pulseMeshRef.current) {
      pulseMeshRef.current.position.set(params.x0, -params.z0, params.y0);
      pulseMeshRef.current.visible = params.A0 > 0;
    }
  }, [params.x0, params.y0, params.z0, params.A0]);

  useEffect(() => {
    sensorMeshesRef.current.forEach((item) => {
      const data = sensors.find((s) => s.id === item.id);
      if (!data) return;
      const { color, emissive, emissiveIntensity } = colorSensorPorSenal(data.signalLevel, data.status);
      item.mat.color.setHex(color);
      item.mat.emissive.setHex(emissive);
      item.mat.emissiveIntensity = emissiveIntensity;
    });
  }, [sensors]);

  return (
    <div className="glass-panel wave-canvas">
      <canvas ref={canvasRef} className="scene-canvas" />
      <div className="scene-overlay">
        Simulacion 3D: Sismo y Sensores<br />
        <span>Color = intensidad relativa A_zi (Ecuacion 1)</span>
      </div>
    </div>
  );
}
