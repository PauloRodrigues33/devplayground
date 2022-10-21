import type { NextPage } from 'next'
import Head from 'next/head'
import { useEffect } from 'react';
import 'swiper/css';
import * as THREE from 'three';

const Home: NextPage = () => {


  const createScene = () => {
    var scene = new THREE.Scene();
    var camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 2000);
    camera.position.z = 5;
    var renderer = new THREE.WebGLRenderer();
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.setSize(window.innerWidth, window.innerHeight);
    document.getElementById('3d')?.appendChild(renderer.domElement);

    var geometry = new THREE.BoxGeometry(1, 1, 1);
    var material = new THREE.MeshStandardMaterial({ color: '#fff', opacity: 1 });
    material.side = THREE.DoubleSide;
    var cube = new THREE.Mesh(geometry, material);
    cube.castShadow = true;
    scene.add(cube);

    var planeGeometry = new THREE.PlaneGeometry(100, 100);
    var plane = new THREE.Mesh(planeGeometry, material);
    plane.rotateX(90);
    plane.position.setY(-15);
    plane.receiveShadow = true;
    plane.castShadow = true;
    scene.add(plane);

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.2);
    const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
    directionalLight.castShadow = true;
    directionalLight.shadow.mapSize.width = 512; // default
    directionalLight.shadow.mapSize.height = 512; // default
    directionalLight.shadow.camera.near = 0.5; // default
    directionalLight.shadow.camera.far = 2000; // default
    directionalLight.position.set(10, 10, 0);
    scene.add(ambientLight);
    scene.add(directionalLight);

    // const helper = new THREE.CameraHelper(directionalLight.shadow.camera);
    // scene.add(helper);

    const Update = () => {
      requestAnimationFrame(Update);
      cube.rotation.x += 0.01;
      cube.rotation.y += 0.01;
      renderer.render(scene, camera);
    }

    Update();
  }

  useEffect(() => {
    createScene();
  }, []);


  return (
    <div>
      <Head>
        <title>Developers Playground</title>
        <meta name="description" content="A open source project to developers test their ideas" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      <main>
        <div id='3d'></div>
        <div style={{ position: 'absolute', top: '0', left: '0', width: '100%', textAlign: 'center', fontSize: '32px', marginTop: '20px' }}>A cube rotating in your X, Y quaternions</div>
      </main>
    </div>
  )
}

export default Home
